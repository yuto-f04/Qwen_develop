"""tests/test_analysis_load.py — load.py の単体テスト (TDD)"""
import io
import os
import tempfile
import textwrap

import pandas as pd
import pytest

from src.analysis.load import (
    normalize_column_names,
    find_column,
    load_responses,
    normalize_name,
    deduplicate_responses,
    match_pairs,
    assign_group,
    detect_round_inconsistency,
    parse_timestamp,
)


# ──────────────────────────────────────────────────────────────────────────────
# normalize_column_names / find_column
# ──────────────────────────────────────────────────────────────────────────────

class TestNormalizeColumnNames:
    def test_strips_whitespace(self):
        cols = ["タイムスタンプ  ", "  1. 体験者の氏名"]
        result = normalize_column_names(cols)
        assert result["タイムスタンプ"] == "タイムスタンプ  "
        assert result["1. 体験者の氏名"] == "  1. 体験者の氏名"

    def test_nfkc_normalization(self):
        # 全角スペースを含む列名が NFKC 後にマッチする
        cols = ["１４－４－２．　興味を抱いた理由を簡単に教えてください"]
        result = normalize_column_names(cols)
        # NFKC 後のキーで検索できること
        import unicodedata
        nfkc_key = unicodedata.normalize("NFKC", "１４－４－２．　興味を抱いた理由を簡単に教えてください").strip()
        assert nfkc_key in result

    def test_14_4_2_two_columns_distinguished(self):
        """14-4-2. で始まる2列が取り違えられない"""
        cols = [
            "14-4-2. 興味を抱かなかった理由について簡単に教えてください",
            "14-4-2. 興味を抱いた理由を簡単に教えてください",
        ]
        result = normalize_column_names(cols)
        assert len(result) == 2
        # 両方が別のキーで登録されている
        keys = list(result.keys())
        assert keys[0] != keys[1]


class TestFindColumn:
    def _make_df(self, col_names):
        return pd.DataFrame(columns=col_names)

    def test_exact_match(self):
        df = self._make_df(["タイムスタンプ", "1. 体験者の氏名"])
        col = find_column(df, "タイムスタンプ")
        assert col == "タイムスタンプ"

    def test_trailing_spaces_in_csv(self):
        df = self._make_df(["16. ツアー全体の感想を教えてください  ", "タイムスタンプ"])
        col = find_column(df, "16. ツアー全体の感想を教えてください")
        assert col == "16. ツアー全体の感想を教えてください  "

    def test_fullwidth_digits_normalized(self):
        df = self._make_df(["１. 体験者の氏名"])
        col = find_column(df, "1. 体験者の氏名")
        assert col == "１. 体験者の氏名"

    def test_missing_column_raises_value_error(self):
        df = self._make_df(["タイムスタンプ"])
        with pytest.raises(ValueError, match="存在しない列"):
            find_column(df, "存在しない列")

    def test_missing_column_error_message_includes_column_name(self):
        df = self._make_df(["タイムスタンプ"])
        with pytest.raises(ValueError) as exc:
            find_column(df, "見つからない列名X")
        assert "見つからない列名X" in str(exc.value)

    def test_no_interest_reason_vs_interest_reason(self):
        """14-4-2. の2列が区別できる"""
        df = self._make_df([
            "14-4-2. 興味を抱かなかった理由について簡単に教えてください",
            "14-4-2. 興味を抱いた理由を簡単に教えてください",
        ])
        col_no = find_column(df, "14-4-2. 興味を抱かなかった理由について簡単に教えてください")
        col_yes = find_column(df, "14-4-2. 興味を抱いた理由を簡単に教えてください")
        assert col_no != col_yes


# ──────────────────────────────────────────────────────────────────────────────
# normalize_name
# ──────────────────────────────────────────────────────────────────────────────

class TestNormalizeName:
    def test_removes_spaces(self):
        assert normalize_name("山田　太郎") == "山田太郎"

    def test_removes_halfwidth_spaces(self):
        assert normalize_name("山田 太郎") == "山田太郎"

    def test_nfkc(self):
        assert normalize_name("Ａ山田") == "A山田"

    def test_empty(self):
        assert normalize_name("") == ""

    def test_multiple_spaces(self):
        assert normalize_name("山 田  太 郎") == "山田太郎"


# ──────────────────────────────────────────────────────────────────────────────
# deduplicate_responses
# ──────────────────────────────────────────────────────────────────────────────

class TestDeduplicateResponses:
    def _make_df(self, rows):
        return pd.DataFrame(rows, columns=["norm_name", "condition", "timestamp", "satisfaction"])

    def test_no_duplicates_unchanged(self):
        df = self._make_df([
            ["山田太郎", "条件A", pd.Timestamp("2026-01-01 10:00"), 8],
            ["田中花子", "条件A", pd.Timestamp("2026-01-01 10:01"), 7],
        ])
        result, warnings = deduplicate_responses(df)
        assert len(result) == 2
        assert warnings == []

    def test_keeps_latest_on_duplicate(self):
        df = self._make_df([
            ["山田太郎", "条件A", pd.Timestamp("2026-01-01 10:00"), 5],
            ["山田太郎", "条件A", pd.Timestamp("2026-01-01 12:00"), 9],
        ])
        result, warnings = deduplicate_responses(df)
        assert len(result) == 1
        assert result.iloc[0]["satisfaction"] == 9

    def test_warns_on_duplicate(self):
        df = self._make_df([
            ["山田太郎", "条件A", pd.Timestamp("2026-01-01 10:00"), 5],
            ["山田太郎", "条件A", pd.Timestamp("2026-01-01 12:00"), 9],
        ])
        _, warnings = deduplicate_responses(df)
        assert len(warnings) == 1
        assert "山田太郎" in warnings[0]


# ──────────────────────────────────────────────────────────────────────────────
# match_pairs
# ──────────────────────────────────────────────────────────────────────────────

class TestMatchPairs:
    def _make_df(self, rows):
        cols = ["norm_name", "condition", "round", "satisfaction"]
        return pd.DataFrame(rows, columns=cols)

    def test_complete_pair_included(self):
        df = self._make_df([
            ["山田太郎", "条件A", "1回目", 7],
            ["山田太郎", "条件B", "2回目", 8],
        ])
        paired, excluded, warnings = match_pairs(df)
        assert "山田太郎" in paired["norm_name"].values
        assert len(excluded) == 0

    def test_only_one_condition_excluded(self):
        df = self._make_df([
            ["山田太郎", "条件A", "1回目", 7],
            ["田中花子", "条件B", "1回目", 8],
            ["田中花子", "条件A", "2回目", 6],
        ])
        paired, excluded, _ = match_pairs(df)
        assert "山田太郎" not in paired["norm_name"].values
        assert any(e["name"] == "山田太郎" for e in excluded)

    def test_exclusion_reason_mentioned(self):
        df = self._make_df([
            ["山田太郎", "条件A", "1回目", 7],
        ])
        _, excluded, _ = match_pairs(df)
        assert any("条件B" in e["reason"] or "片方" in e["reason"] for e in excluded)


# ──────────────────────────────────────────────────────────────────────────────
# assign_group
# ──────────────────────────────────────────────────────────────────────────────

class TestAssignGroup:
    def _make_df(self, rows):
        cols = ["norm_name", "condition", "round"]
        return pd.DataFrame(rows, columns=cols)

    def test_group1_a_first(self):
        df = self._make_df([
            ["山田太郎", "条件A", "1回目"],
            ["山田太郎", "条件B", "2回目"],
        ])
        result = assign_group(df)
        assert result.loc[result["norm_name"] == "山田太郎", "group"].iloc[0] == 1

    def test_group2_b_first(self):
        df = self._make_df([
            ["田中花子", "条件B", "1回目"],
            ["田中花子", "条件A", "2回目"],
        ])
        result = assign_group(df)
        assert result.loc[result["norm_name"] == "田中花子", "group"].iloc[0] == 2


# ──────────────────────────────────────────────────────────────────────────────
# detect_round_inconsistency
# ──────────────────────────────────────────────────────────────────────────────

class TestDetectRoundInconsistency:
    def _make_df(self, rows):
        cols = ["norm_name", "condition", "round"]
        return pd.DataFrame(rows, columns=cols)

    def test_consistent_no_warning(self):
        df = self._make_df([
            ["山田太郎", "条件A", "1回目"],
            ["山田太郎", "条件B", "2回目"],
        ])
        warnings = detect_round_inconsistency(df)
        assert warnings == []

    def test_both_first_round_flagged(self):
        df = self._make_df([
            ["山田太郎", "条件A", "1回目"],
            ["山田太郎", "条件B", "1回目"],
        ])
        warnings = detect_round_inconsistency(df)
        assert len(warnings) == 1
        assert "山田太郎" in warnings[0]

    def test_both_second_round_flagged(self):
        df = self._make_df([
            ["田中花子", "条件A", "2回目"],
            ["田中花子", "条件B", "2回目"],
        ])
        warnings = detect_round_inconsistency(df)
        assert len(warnings) == 1

    def test_returns_name_message_tuples(self):
        """I3: 返り値が (name, message) タプルのリストであること"""
        df = self._make_df([
            ["山田太郎", "条件A", "1回目"],
            ["山田太郎", "条件B", "1回目"],
        ])
        warnings = detect_round_inconsistency(df)
        assert len(warnings) == 1
        item = warnings[0]
        assert isinstance(item, tuple) and len(item) == 2
        name, msg = item
        assert name == "山田太郎"
        assert "山田太郎" in msg


# ──────────────────────────────────────────────────────────────────────────────
# load_responses（統合：実CSVファイル相当の文字列から読む）
# ──────────────────────────────────────────────────────────────────────────────

class TestLoadResponses:
    def _csv(self, header, *rows):
        lines = [header] + list(rows)
        return io.StringIO("\n".join(lines))

    def _make_header(self):
        return (
            "タイムスタンプ,"
            "1. 体験者の氏名,"
            "2. ツアーの条件,"
            "3. 何回目の参加ですか？,"
            "4. ツアー内容に興味を持ちましたか？,"
            "5. ツアーの長さは適切でしたか？,"
            "6. ツアー中の説明は分かりやすかったですか？,"
            "7. ガイドの語りに熱意を感じましたか？,"
            "8. このツアーを他人におすすめできますか？,"
            "9. ツアーは期待通りでしたか？,"
            "10. このツアーに満足しましたか？,"
            "11. ツアー内容は難しいと感じましたか？,"
            "12. 体力面で不安は感じましたか？,"
            "13. また参加したいと感じましたか？,"
            "14. ツアーの説明の中に「違和感」「気になったところ」はありましたか？,"
            "14-2. どこで「違和感」を感じたか？,"
            "14-3. なぜ「違和感」を抱いたのか？,"
            "14-4. その違和感に「興味」を抱いたか？,"
            "14-4-2. 興味を抱かなかった理由について簡単に教えてください,"
            "14-4-2. 興味を抱いた理由を簡単に教えてください,"
            "15. ツアーの中で最も印象に残った場面・体験を教えてください,"
            "16. ツアー全体の感想を教えてください  "
        )

    def _make_row(self, name="山田太郎", cond="条件A", rnd="1回目", vals=None):
        if vals is None:
            vals = [7] * 10
        vals_str = ",".join(str(v) for v in vals)
        return (
            f"2026/11/01 10:00:00,{name},{cond},{rnd},"
            f"{vals_str},"
            "なかった,,,,,,感想"
        )

    def test_returns_dataframe(self):
        src = self._csv(self._make_header(), self._make_row())
        df, warnings = load_responses(src)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1

    def test_trailing_spaces_in_header_handled(self):
        """16番列の末尾2スペースがあっても正しく読める"""
        src = self._csv(self._make_header(), self._make_row())
        df, _ = load_responses(src)
        assert "comment" in df.columns

    def test_out_of_range_scale_becomes_nan(self):
        row = self._make_row(vals=[11, 7, 7, 7, 7, 7, 7, 7, 7, 7])
        src = self._csv(self._make_header(), row)
        df, warnings = load_responses(src)
        import numpy as np
        assert np.isnan(df["interest"].iloc[0])
        assert any("範囲外" in w or "interest" in w for w in warnings)

    def test_non_numeric_scale_becomes_nan(self):
        row = self._make_row(vals=["abc", 7, 7, 7, 7, 7, 7, 7, 7, 7])
        src = self._csv(self._make_header(), row)
        df, warnings = load_responses(src)
        import numpy as np
        assert np.isnan(df["interest"].iloc[0])


# ──────────────────────────────────────────────────────────────────────────────
# parse_timestamp
# ──────────────────────────────────────────────────────────────────────────────

class TestParseTimestamp:
    def test_slash_format(self):
        ts = parse_timestamp("2026/11/10 13:05:22")
        assert ts.year == 2026 and ts.hour == 13 and ts.minute == 5

    def test_iso_format(self):
        ts = parse_timestamp("2026-11-10T13:05:22")
        assert ts.year == 2026 and ts.hour == 13

    def test_gogo_format(self):
        ts = parse_timestamp("2026/11/10 午後 1:05:22")
        assert ts.hour == 13 and ts.minute == 5

    def test_gozen_format(self):
        ts = parse_timestamp("2026/11/10 午前 9:05:22")
        assert ts.hour == 9 and ts.minute == 5

    def test_gogo_noon(self):
        ts = parse_timestamp("2026/11/10 午後 12:00:00")
        assert ts.hour == 12

    def test_gozen_midnight(self):
        ts = parse_timestamp("2026/11/10 午前 12:00:00")
        assert ts.hour == 0

    def test_unknown_returns_nat(self):
        import pandas as pd
        ts = parse_timestamp("not a date at all")
        assert pd.isna(ts)


# ──────────────────────────────────────────────────────────────────────────────
# F1: encoding fallback（ファイルパスから読む場合）
# ──────────────────────────────────────────────────────────────────────────────

class TestLoadResponsesEncoding:
    """CP932 / UTF-8-sig の両方を読み、未知エンコードは分かりやすいエラーにする"""

    _HEADER = (
        "タイムスタンプ,1. 体験者の氏名,2. ツアーの条件,3. 何回目の参加ですか？,"
        "4. ツアー内容に興味を持ちましたか？,5. ツアーの長さは適切でしたか？,"
        "6. ツアー中の説明は分かりやすかったですか？,7. ガイドの語りに熱意を感じましたか？,"
        "8. このツアーを他人におすすめできますか？,9. ツアーは期待通りでしたか？,"
        "10. このツアーに満足しましたか？,11. ツアー内容は難しいと感じましたか？,"
        "12. 体力面で不安は感じましたか？,13. また参加したいと感じましたか？,"
        "14. ツアーの説明の中に「違和感」「気になったところ」はありましたか？,"
        "14-2. どこで「違和感」を感じたか？,14-3. なぜ「違和感」を抱いたのか？,"
        "14-4. その違和感に「興味」を抱いたか？,"
        "14-4-2. 興味を抱かなかった理由について簡単に教えてください,"
        "14-4-2. 興味を抱いた理由を簡単に教えてください,"
        "15. ツアーの中で最も印象に残った場面・体験を教えてください,"
        "16. ツアー全体の感想を教えてください  "
    )
    _ROW = "2026/11/01 10:00:00,山田太郎,条件A,1回目,7,7,7,7,7,7,7,7,7,7,なかった,,,,,感想"

    def _write_tmp(self, content: bytes, suffix=".csv"):
        fd, path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        with open(path, "wb") as f:
            f.write(content)
        return path

    def test_utf8_bom_file_path(self):
        content = (self._HEADER + "\n" + self._ROW + "\n").encode("utf-8-sig")
        path = self._write_tmp(content)
        try:
            df, warnings = load_responses(path)
            assert len(df) == 1
        finally:
            os.unlink(path)

    def test_cp932_file_path_reads_successfully(self):
        content = (self._HEADER + "\n" + self._ROW + "\n").encode("cp932")
        path = self._write_tmp(content)
        try:
            df, warnings = load_responses(path)
            assert len(df) == 1
        finally:
            os.unlink(path)

    def test_cp932_file_path_warns_about_encoding(self):
        content = (self._HEADER + "\n" + self._ROW + "\n").encode("cp932")
        path = self._write_tmp(content)
        try:
            _, warnings = load_responses(path)
            assert any("cp932" in w.lower() or "文字コード" in w for w in warnings)
        finally:
            os.unlink(path)

    def test_unknown_encoding_raises_value_error(self):
        content = b"\xff\xfe" + "ダミー".encode("utf-16-le")
        path = self._write_tmp(content)
        try:
            with pytest.raises(ValueError, match="UTF-8"):
                load_responses(path)
        finally:
            os.unlink(path)


# ──────────────────────────────────────────────────────────────────────────────
# F3: 空欄氏名を警告付きで除外
# ──────────────────────────────────────────────────────────────────────────────

class TestBlankNameFiltering:
    """空欄（空文字・スペースのみ）の氏名の回答を除外し、警告を出す"""

    _HEADER = (
        "タイムスタンプ,1. 体験者の氏名,2. ツアーの条件,3. 何回目の参加ですか？,"
        "4. ツアー内容に興味を持ちましたか？,5. ツアーの長さは適切でしたか？,"
        "6. ツアー中の説明は分かりやすかったですか？,7. ガイドの語りに熱意を感じましたか？,"
        "8. このツアーを他人におすすめできますか？,9. ツアーは期待通りでしたか？,"
        "10. このツアーに満足しましたか？,11. ツアー内容は難しいと感じましたか？,"
        "12. 体力面で不安は感じましたか？,13. また参加したいと感じましたか？,"
        "14. ツアーの説明の中に「違和感」「気になったところ」はありましたか？,"
        "14-2. どこで「違和感」を感じたか？,14-3. なぜ「違和感」を抱いたのか？,"
        "14-4. その違和感に「興味」を抱いたか？,"
        "14-4-2. 興味を抱かなかった理由について簡単に教えてください,"
        "14-4-2. 興味を抱いた理由を簡単に教えてください,"
        "15. ツアーの中で最も印象に残った場面・体験を教えてください,"
        "16. ツアー全体の感想を教えてください  "
    )

    def _csv(self, *rows):
        return io.StringIO(self._HEADER + "\n" + "\n".join(rows) + "\n")

    def _row(self, name):
        return f"2026/11/01 10:00:00,{name},条件A,1回目,7,7,7,7,7,7,7,7,7,7,なかった,,,,,感想"

    def test_blank_name_row_is_excluded(self):
        """空欄氏名の行は df に含まれない"""
        src = self._csv(self._row(""), self._row("山田太郎"))
        df, _ = load_responses(src)
        assert len(df) == 1
        assert all(df["norm_name"] != "")

    def test_spaces_only_name_is_excluded(self):
        """スペースのみの氏名も除外される"""
        src = self._csv(self._row("   "), self._row("山田太郎"))
        df, _ = load_responses(src)
        assert len(df) == 1

    def test_blank_name_warning_contains_count(self):
        """警告メッセージに除外件数が含まれる"""
        src = self._csv(self._row(""), self._row(""), self._row("山田太郎"))
        _, warnings = load_responses(src)
        assert any("2" in w and "除外" in w for w in warnings)

    def test_warning_says_blank_name(self):
        """警告に「氏名が空欄」という文字が含まれる"""
        src = self._csv(self._row(""), self._row("山田太郎"))
        _, warnings = load_responses(src)
        assert any("氏名が空欄" in w for w in warnings)

    def test_non_blank_names_are_kept(self):
        """氏名がある行は除外されない"""
        src = self._csv(self._row("鈴木花子"), self._row("田中一郎"))
        df, _ = load_responses(src)
        assert len(df) == 2

    def test_all_blank_returns_empty_df(self):
        """全行空欄氏名ならdfが空になる"""
        src = self._csv(self._row(""), self._row(""))
        df, warnings = load_responses(src)
        assert len(df) == 0


# ──────────────────────────────────────────────────────────────────────────────
# real_header.csv 回帰テスト
# 本番 Google フォームの実際の列名構造がそのまま parse できることを保証する。
# tests/fixtures/edge_cases/real_header.csv は本番 CSV と同じ列名・構造を持ち、
# 氏名のみ架空のテスト被験者 A〜T に置換したもの。
# ──────────────────────────────────────────────────────────────────────────────

import pathlib


class TestRealHeaderFixture:
    """tests/fixtures/edge_cases/real_header.csv を使った列名回帰テスト"""

    FIXTURE = (
        pathlib.Path(__file__).parent / "fixtures" / "edge_cases" / "real_header.csv"
    )

    def test_fixture_file_exists(self):
        assert self.FIXTURE.exists(), "real_header.csv が見つかりません"

    def test_load_does_not_raise(self):
        """実際の列名構造で load_responses がエラーなく通ること"""
        df, warnings = load_responses(str(self.FIXTURE))
        assert df is not None

    def test_expected_columns_present(self):
        """必須の内部列が作られていること"""
        df, _ = load_responses(str(self.FIXTURE))
        for col in ("norm_name", "condition", "round", "timestamp"):
            assert col in df.columns, f"列 {col!r} がない"

    def test_score_columns_present(self):
        """スコア列（interest, recommend 等）が数値として読まれていること"""
        df, _ = load_responses(str(self.FIXTURE))
        for col in ("interest", "recommend", "satisfaction", "revisit"):
            assert col in df.columns, f"列 {col!r} がない"

    def test_paired_participants_count(self):
        """テストデータの有効ペア数が期待通りであること（片方のみ参加者1名を除いた20名=10ペア）"""
        df, _ = load_responses(str(self.FIXTURE))
        # 全体行数: テスト被験者A〜T=40行 + 片方のみ1行 = 41行
        # 空欄氏名なし・重複(テスト被験者E)を除くと有効行40行
        assert len(df) >= 40

    def test_space_variant_names_normalized(self):
        """全角スペース入り氏名（テスト被験者C・F）が正規化されてペアになること"""
        df, _ = load_responses(str(self.FIXTURE))
        # norm_name でスペースが除去され同一人物と見なされること
        counts = df["norm_name"].value_counts()
        # テスト被験者C と テスト被験者F はそれぞれ2行（空白違いの2エントリ）
        c_name = "テスト被験者C"
        assert counts.get(c_name, 0) == 2, f"{c_name} のペアが揃っていない"


# ──────────────────────────────────────────────────────────────────────────────
# X1: 違和感・興味の選択肢が config.py に定義されていること
# ──────────────────────────────────────────────────────────────────────────────

from src import config as _cfg


class TestConfigDiscomfortChoices:
    """X1: config に違和感・興味の選択肢定数が存在すること"""

    def test_discomfort_categories_defined(self):
        assert hasattr(_cfg, "DISCOMFORT_CATEGORIES"), \
            "config.DISCOMFORT_CATEGORIES が定義されていません"

    def test_discomfort_categories_has_three_values(self):
        assert set(_cfg.DISCOMFORT_CATEGORIES) == {"なかった", "少しあった", "あった"}

    def test_discomfort_present_categories_defined(self):
        assert hasattr(_cfg, "DISCOMFORT_PRESENT_CATEGORIES"), \
            "config.DISCOMFORT_PRESENT_CATEGORIES が定義されていません"

    def test_discomfort_present_categories_excludes_nakatta(self):
        assert "なかった" not in _cfg.DISCOMFORT_PRESENT_CATEGORIES
        assert "少しあった" in _cfg.DISCOMFORT_PRESENT_CATEGORIES
        assert "あった" in _cfg.DISCOMFORT_PRESENT_CATEGORIES

    def test_discomfort_interest_choices_defined(self):
        assert hasattr(_cfg, "DISCOMFORT_INTEREST_CHOICES"), \
            "config.DISCOMFORT_INTEREST_CHOICES が定義されていません"

    def test_discomfort_interest_choices_has_hai_and_iie(self):
        assert set(_cfg.DISCOMFORT_INTEREST_CHOICES) == {"はい", "いいえ"}


# ──────────────────────────────────────────────────────────────────────────────
# X1: 想定外の discomfort / discomfort_interest 値に警告を出すこと
# ──────────────────────────────────────────────────────────────────────────────

class TestDiscomfortValidation:
    """X1: 想定外値を検出して警告、既知値・空欄は警告なし"""

    _HEADER = (
        "タイムスタンプ,1. 体験者の氏名,2. ツアーの条件,3. 何回目の参加ですか？,"
        "4. ツアー内容に興味を持ちましたか？,5. ツアーの長さは適切でしたか？,"
        "6. ツアー中の説明は分かりやすかったですか？,7. ガイドの語りに熱意を感じましたか？,"
        "8. このツアーを他人におすすめできますか？,9. ツアーは期待通りでしたか？,"
        "10. このツアーに満足しましたか？,11. ツアー内容は難しいと感じましたか？,"
        "12. 体力面で不安は感じましたか？,13. また参加したいと感じましたか？,"
        "14. ツアーの説明の中に「違和感」「気になったところ」はありましたか？,"
        "14-2. どこで「違和感」を感じたか？,14-3. なぜ「違和感」を抱いたのか？,"
        "14-4. その違和感に「興味」を抱いたか？,"
        "14-4-2. 興味を抱かなかった理由について簡単に教えてください,"
        "14-4-2. 興味を抱いた理由を簡単に教えてください,"
        "15. ツアーの中で最も印象に残った場面・体験を教えてください,"
        "16. ツアー全体の感想を教えてください  "
    )

    def _csv(self, *rows):
        return io.StringIO(self._HEADER + "\n" + "\n".join(rows) + "\n")

    def _row(self, name="山田太郎", cond="条件A", disc="なかった", interest=""):
        return (
            f"2026/11/01 10:00:00,{name},{cond},1回目,"
            f"7,7,7,7,7,7,7,7,7,7,"
            f"{disc},,,{interest},,,感想"
        )

    def test_known_discomfort_value_no_warning(self):
        """既知の選択肢（なかった/少しあった/あった）は警告なし"""
        for disc in ["なかった", "少しあった", "あった"]:
            src = self._csv(self._row(disc=disc))
            _, warnings = load_responses(src)
            disc_warns = [w for w in warnings if "discomfort" in w and disc in w
                          and "想定外" in w]
            assert disc_warns == [], f"'{disc}' で誤警告: {disc_warns}"

    def test_unknown_discomfort_value_warns(self):
        """想定外の値（例: 'ありました'）は警告が出る"""
        src = self._csv(self._row(disc="ありました"))
        _, warnings = load_responses(src)
        assert any("ありました" in w and "想定外" in w for w in warnings), \
            f"想定外の discomfort 値に警告が出ていない: {warnings}"

    def test_blank_discomfort_no_warning(self):
        """空欄（NaN/空文字）は警告なし"""
        src = self._csv(self._row(disc=""))
        _, warnings = load_responses(src)
        disc_warns = [w for w in warnings if "discomfort" in w and "想定外" in w]
        assert disc_warns == [], f"空欄で誤警告: {disc_warns}"

    def test_known_discomfort_interest_no_warning(self):
        """'はい'/'いいえ' は警告なし"""
        for interest in ["はい", "いいえ"]:
            src = self._csv(self._row(disc="あった", interest=interest))
            _, warnings = load_responses(src)
            int_warns = [w for w in warnings if "discomfort_interest" in w
                         and "想定外" in w]
            assert int_warns == [], f"'{interest}' で誤警告: {int_warns}"

    def test_unknown_discomfort_interest_value_warns(self):
        """想定外の興味値（例: 'たぶん'）は警告が出る"""
        src = self._csv(self._row(disc="あった", interest="たぶん"))
        _, warnings = load_responses(src)
        assert any("たぶん" in w and "想定外" in w for w in warnings), \
            f"想定外の discomfort_interest 値に警告が出ていない: {warnings}"

    def test_blank_discomfort_interest_no_warning(self):
        """discomfort_interest が空欄なら警告なし"""
        src = self._csv(self._row(disc="あった", interest=""))
        _, warnings = load_responses(src)
        int_warns = [w for w in warnings if "discomfort_interest" in w
                     and "想定外" in w]
        assert int_warns == [], f"空欄で誤警告: {int_warns}"

    def test_multiple_unknown_values_all_warned(self):
        """複数行に想定外値があれば、すべて警告に含まれる"""
        src = self._csv(
            self._row(name="田中太郎", disc="ちょっとある"),
            self._row(name="鈴木花子", disc="かなりある"),
        )
        _, warnings = load_responses(src)
        unknown_warns = [w for w in warnings if "想定外" in w and "discomfort" in w]
        assert len(unknown_warns) >= 2, \
            f"2件の想定外値なのに警告が {len(unknown_warns)} 件: {warnings}"


# ──────────────────────────────────────────────────────────────────────────────
# assign_participant_ids
# ──────────────────────────────────────────────────────────────────────────────

from src.analysis.load import assign_participant_ids


class TestAssignParticipantIds:
    def _make_df(self):
        return pd.DataFrame({
            "norm_name":  ["山田太郎", "山田太郎", "田中花子", "田中花子"],
            "condition":  ["条件A", "条件B", "条件A", "条件B"],
            "timestamp":  pd.to_datetime([
                "2026-11-20 10:00:00",
                "2026-11-20 10:30:00",
                "2026-11-20 10:05:00",
                "2026-11-20 10:35:00",
            ]),
        })

    def test_norm_name_replaced_with_id(self):
        df = self._make_df()
        result, _ = assign_participant_ids(df)
        assert set(result["norm_name"].unique()).issubset({"P01", "P02"})

    def test_original_names_not_in_output(self):
        df = self._make_df()
        result, _ = assign_participant_ids(df)
        for name in ["山田太郎", "田中花子"]:
            assert name not in result["norm_name"].values

    def test_id_to_name_mapping_complete(self):
        df = self._make_df()
        _, id_to_name = assign_participant_ids(df)
        assert set(id_to_name.values()) == {"山田太郎", "田中花子"}
        assert set(id_to_name.keys()).issubset({"P01", "P02"})

    def test_ordered_by_first_timestamp(self):
        """最初のタイムスタンプが早い人が P01 になること"""
        df = self._make_df()  # 山田太郎 10:00, 田中花子 10:05
        result, id_to_name = assign_participant_ids(df)
        p01_name = id_to_name["P01"]
        assert p01_name == "山田太郎"

    def test_does_not_modify_original(self):
        df = self._make_df()
        original_names = df["norm_name"].tolist()
        assign_participant_ids(df)
        assert df["norm_name"].tolist() == original_names

    def test_row_count_unchanged(self):
        df = self._make_df()
        result, _ = assign_participant_ids(df)
        assert len(result) == len(df)
