"""tests/test_analysis_report.py -- エンドツーエンドテスト (TDD)

ダミーデータで run_analysis を最後まで実行し、
report.md・図・CSVがすべて作られることを確認する。
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

_UTF8_ENV = {**os.environ, "PYTHONIOENCODING": "utf-8"}


@pytest.fixture(scope="module")
def run_with_dummy():
    """make_dummy_data で CSV を作り、run_analysis を実行して出力ディレクトリを返す"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        input_csv = tmpdir / "responses.csv"
        outdir = tmpdir / "output"

        # ダミーデータ生成
        result = subprocess.run(
            [sys.executable, "scripts/make_dummy_data.py", "--output", str(input_csv)],
            capture_output=True, text=True, encoding="utf-8", env=_UTF8_ENV,
        )
        assert result.returncode == 0, f"make_dummy_data failed:\n{result.stderr}"

        # 分析実行
        result = subprocess.run(
            [sys.executable, "run_analysis.py",
             "--input", str(input_csv),
             "--outdir", str(outdir)],
            capture_output=True, text=True, encoding="utf-8", env=_UTF8_ENV,
        )
        assert result.returncode == 0, (
            f"run_analysis failed:\n{result.stdout}\n{result.stderr}"
        )
        yield outdir, result.stdout


class TestOutputFilesExist:
    def test_report_md_created(self, run_with_dummy):
        outdir, _ = run_with_dummy
        assert (outdir / "report.md").exists()

    def test_tidy_csv_created(self, run_with_dummy):
        outdir, _ = run_with_dummy
        assert (outdir / "tidy.csv").exists()

    def test_wide_csv_created(self, run_with_dummy):
        outdir, _ = run_with_dummy
        assert (outdir / "wide.csv").exists()

    def test_free_text_csv_created(self, run_with_dummy):
        outdir, _ = run_with_dummy
        assert (outdir / "free_text.csv").exists()

    def test_coding_sheet_csv_created(self, run_with_dummy):
        outdir, _ = run_with_dummy
        assert (outdir / "coding_sheet.csv").exists()

    def test_lie_list_csv_created(self, run_with_dummy):
        outdir, _ = run_with_dummy
        assert (outdir / "lie_list.csv").exists()

    def test_figures_dir_created(self, run_with_dummy):
        outdir, _ = run_with_dummy
        assert (outdir / "figures").is_dir()

    def test_figure_main_metric_created(self, run_with_dummy):
        outdir, _ = run_with_dummy
        figs = list((outdir / "figures").glob("*.png"))
        assert len(figs) >= 3, f"図が3枚以上あること: {figs}"


class TestReportContent:
    def test_report_has_data_overview(self, run_with_dummy):
        outdir, _ = run_with_dummy
        report = (outdir / "report.md").read_text(encoding="utf-8")
        assert "データ" in report or "回答数" in report

    def test_report_has_primary_metric_section(self, run_with_dummy):
        outdir, _ = run_with_dummy
        report = (outdir / "report.md").read_text(encoding="utf-8")
        assert "主指標" in report

    def test_report_has_judgment_text(self, run_with_dummy):
        outdir, _ = run_with_dummy
        report = (outdir / "report.md").read_text(encoding="utf-8")
        assert "仮説" in report or "得られなかった" in report or "高かった" in report

    def test_report_has_secondary_section(self, run_with_dummy):
        outdir, _ = run_with_dummy
        report = (outdir / "report.md").read_text(encoding="utf-8")
        assert "副指標" in report

    def test_report_has_discomfort_section(self, run_with_dummy):
        outdir, _ = run_with_dummy
        report = (outdir / "report.md").read_text(encoding="utf-8")
        assert "違和感" in report

    def test_report_has_ceiling_effect_section(self, run_with_dummy):
        outdir, _ = run_with_dummy
        report = (outdir / "report.md").read_text(encoding="utf-8")
        assert "天井" in report or "記述統計" in report


class TestTerminalOutput:
    def test_terminal_shows_primary_metric_result(self, run_with_dummy):
        _, stdout = run_with_dummy
        assert "主指標" in stdout or "p値" in stdout or "p =" in stdout

    def test_terminal_shows_judgment(self, run_with_dummy):
        _, stdout = run_with_dummy
        assert "仮説" in stdout or "得られなかった" in stdout or "高かった" in stdout


# ──────────────────────────────────────────────────────────────────────────────
# F2: 空データ・全員同条件・1件のみでクラッシュしないこと
# ──────────────────────────────────────────────────────────────────────────────

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
_ROW_A = "2026/11/01 10:00:00,テスト太郎,条件A,1回目,7,7,7,7,7,7,7,7,7,7,なかった,,,,,感想"
_ROW_B = "2026/11/01 11:00:00,テスト太郎,条件B,2回目,8,8,8,8,8,8,8,8,8,8,なかった,,,,,感想"


class TestLieIdMatching:
    """I2: 嘘ID照合が分割後の完全一致で行われること"""

    def _make_coding_done(self, rows: list) -> str:
        import csv, io as sio
        buf = sio.StringIO()
        w = csv.DictWriter(buf, fieldnames=["氏名", "該当する嘘ID", "discomfort_interest"])
        w.writeheader()
        for r in rows:
            w.writerow(r)
        return buf.getvalue()

    def _run_with_coding(self, coding_text: str):
        from src.analysis.report import _summarize_lie_detection
        import tempfile, os
        fd, path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        with open(path, "w", encoding="utf-8") as f:
            f.write(coding_text)
        try:
            return _summarize_lie_detection(path)
        finally:
            os.unlink(path)

    def test_h1_does_not_match_h10(self):
        """H1 が仮想の H10 にマッチしないこと（部分一致バグの回帰テスト）"""
        coding = self._make_coding_done([
            {"氏名": "テスト", "該当する嘘ID": "H10", "discomfort_interest": "はい"},
        ])
        result = self._run_with_coding(coding)
        assert result.get("H1", {}).get("n_noticed", 0) == 0

    def test_comma_separated_ids_both_matched(self):
        """'H1,K2' と書いた場合 H1 も K2 も 1 件としてカウント"""
        coding = self._make_coding_done([
            {"氏名": "テスト", "該当する嘘ID": "H1,K2", "discomfort_interest": "はい"},
        ])
        result = self._run_with_coding(coding)
        assert result.get("H1", {}).get("n_noticed", 0) == 1
        assert result.get("K2", {}).get("n_noticed", 0) == 1

    def test_japanese_comma_separated(self):
        """全角カンマ区切りにも対応"""
        coding = self._make_coding_done([
            {"氏名": "テスト", "該当する嘘ID": "H2、L1", "discomfort_interest": "いいえ"},
        ])
        result = self._run_with_coding(coding)
        assert result.get("H2", {}).get("n_noticed", 0) == 1
        assert result.get("L1", {}).get("n_noticed", 0) == 1

    def test_fullwidth_id_normalized(self):
        """全角英数字 'Ｈ１' は 'H1' として認識される"""
        coding = self._make_coding_done([
            {"氏名": "テスト", "該当する嘘ID": "Ｈ１", "discomfort_interest": "はい"},
        ])
        result = self._run_with_coding(coding)
        assert result.get("H1", {}).get("n_noticed", 0) == 1


class TestEmptyDataDoesNotCrash:
    """ペアがゼロになる入力でも ValueError を出して正常終了すること"""

    def _run(self, csv_text: str):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            csv_p = d / "r.csv"
            csv_p.write_text(csv_text, encoding="utf-8")
            out = d / "out"
            env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
            return subprocess.run(
                [sys.executable, "run_analysis.py", "--input", str(csv_p), "--outdir", str(out)],
                capture_output=True, text=True, encoding="utf-8", env=env,
            )

    def test_header_only_exits_cleanly(self):
        result = self._run(_HEADER + "\n")
        assert result.returncode != 0 or "ペア" in result.stdout or "分析対象" in result.stdout
        assert "KeyError" not in result.stderr and "Traceback" not in result.stderr

    def test_one_row_only_exits_cleanly(self):
        result = self._run(_HEADER + "\n" + _ROW_A + "\n")
        assert "KeyError" not in result.stderr and "Traceback" not in result.stderr

    def test_all_same_condition_exits_cleanly(self):
        rows = "\n".join(
            f"2026/11/01 10:00:00,人{i:02d},条件A,1回目,7,7,7,7,7,7,7,7,7,7,なかった,,,,,感想"
            for i in range(5)
        )
        result = self._run(_HEADER + "\n" + rows + "\n")
        assert "KeyError" not in result.stderr and "Traceback" not in result.stderr

    def test_error_message_is_user_friendly(self):
        result = self._run(_HEADER + "\n")
        # エラー時は分かりやすいメッセージが標準出力か標準エラーに出ること
        combined = result.stdout + result.stderr
        assert "ペア" in combined or "分析対象" in combined or "回答" in combined
