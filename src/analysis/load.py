"""src/analysis/load.py — CSVの読み込み・前処理・氏名突き合わせ"""
import unicodedata
import re
from typing import Union, IO, List, Dict, Tuple, Optional

import numpy as np
import pandas as pd

from src import config


def _nfkc_strip(s: str) -> str:
    return unicodedata.normalize("NFKC", s).strip()


# ── タイムスタンプ解析 ──────────────────────────────────────────────────────────

_GOGO_RE = re.compile(
    r"(\d{4}[/\-]\d{1,2}[/\-]\d{1,2})\s+午後\s+(\d{1,2}):(\d{2}):?(\d{2})?"
)
_GOZEN_RE = re.compile(
    r"(\d{4}[/\-]\d{1,2}[/\-]\d{1,2})\s+午前\s+(\d{1,2}):(\d{2}):?(\d{2})?"
)


def parse_timestamp(s: str) -> pd.Timestamp:
    """タイムスタンプ文字列を pd.Timestamp に変換する。
    「午前/午後 H:MM:SS」形式を含む。変換不能なら pd.NaT を返す。
    """
    if not isinstance(s, str):
        return pd.NaT

    # 午後 → 24時間に変換
    m = _GOGO_RE.search(s)
    if m:
        date_part, h, mi, sec = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4) or 0)
        if h != 12:
            h += 12
        norm = f"{date_part} {h:02d}:{mi:02d}:{sec:02d}"
        try:
            return pd.Timestamp(norm)
        except Exception:
            return pd.NaT

    # 午前 → 24時間（12時は0時）
    m = _GOZEN_RE.search(s)
    if m:
        date_part, h, mi, sec = m.group(1), int(m.group(2)), int(m.group(3)), int(m.group(4) or 0)
        if h == 12:
            h = 0
        norm = f"{date_part} {h:02d}:{mi:02d}:{sec:02d}"
        try:
            return pd.Timestamp(norm)
        except Exception:
            return pd.NaT

    # 通常の形式（2026/11/01 10:00:00, ISO8601 等）
    try:
        return pd.Timestamp(s)
    except Exception:
        return pd.NaT


# ── CSV エンコーディング自動判定 ────────────────────────────────────────────────

def _read_csv_auto_encoding(path: str) -> Tuple[pd.DataFrame, str]:
    """UTF-8-sig → CP932 の順に試みて (df, encoding) を返す。
    どちらでも読めない場合は ValueError を送出する。
    """
    for enc in ("utf-8-sig", "cp932"):
        try:
            df = pd.read_csv(path, encoding=enc)
            return df, enc
        except (UnicodeDecodeError, Exception) as e:
            if "codec" not in str(e).lower() and "decode" not in str(e).lower() and "utf" not in str(e).lower():
                # pandas の ParserError など別のエラーはそのまま上げる
                raise
            continue
    raise ValueError(
        "文字コードを判別できません。CSV を UTF-8 で保存し直してください。"
        "（試したエンコード: utf-8, cp932）"
    )


def normalize_column_names(col_names: List[str]) -> Dict[str, str]:
    """NFKC正規化・前後空白除去したキー → 元のカラム名 の辞書を返す"""
    result: Dict[str, str] = {}
    for name in col_names:
        key = _nfkc_strip(name)
        result[key] = name
    return result


def find_column(df: pd.DataFrame, query: str) -> str:
    """query（NFKC正規化済みの想定列名）に一致するdf内の実際の列名を返す。
    見つからなければ ValueError を出す。
    """
    norm_map = normalize_column_names(list(df.columns))
    q_norm = _nfkc_strip(query)
    if q_norm in norm_map:
        return norm_map[q_norm]
    raise ValueError(
        f"列 '{query}' がCSVに存在しません。"
        f"利用可能な列: {list(norm_map.keys())}"
    )


def normalize_name(name: str) -> str:
    """氏名を正規化する: NFKC + すべての空白文字を除去"""
    if not isinstance(name, str):
        return ""
    s = unicodedata.normalize("NFKC", name)
    s = re.sub(r"\s+", "", s)
    return s


def _rename_columns(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """config.COLUMN_MAP に従ってカラム名を内部名にリネームする。
    欠落している列があれば ValueError を出す。
    """
    rename_dict: Dict[str, str] = {}
    for internal, question in config.COLUMN_MAP.items():
        actual = find_column(df, question)
        rename_dict[actual] = internal
    return df.rename(columns=rename_dict), []


def _validate_discomfort(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """discomfort / discomfort_interest の想定外値を警告する。
    NaN・空文字・既知の選択肢以外の値を検出する。
    想定外の値は黙って0件集計されることがないよう、必ず警告を出す。
    """
    warnings: List[str] = []
    checks = [
        ("discomfort", config.DISCOMFORT_CATEGORIES),
        ("discomfort_interest", config.DISCOMFORT_INTEREST_CHOICES),
    ]
    for col, valid_values in checks:
        if col not in df.columns:
            continue
        valid = set(valid_values)
        for idx, val in df[col].items():
            if pd.isna(val) or str(val).strip() == "":
                continue
            if str(val) not in valid:
                warnings.append(
                    f"行{idx}: 列'{col}'の値'{val}'は想定外の値です"
                    f"（想定: {valid_values}）。集計には使用されません。"
                )
    return df, warnings


def _validate_scale(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """スケール項目を数値に変換し、1〜10の範囲外・数値でない場合はNaNにして警告を返す"""
    warnings: List[str] = []
    for col in config.SCALE_ITEMS:
        if col not in df.columns:
            continue
        original = df[col].copy()
        numeric = pd.to_numeric(df[col], errors="coerce")
        out_of_range = numeric.notna() & ((numeric < 1) | (numeric > 10))
        non_numeric = original.notna() & numeric.isna() & (original != "")
        for idx in df.index[out_of_range]:
            warnings.append(
                f"行{idx}: 列'{col}'の値'{original[idx]}'は範囲外（1〜10）のためNaNに変換"
            )
        for idx in df.index[non_numeric]:
            warnings.append(
                f"行{idx}: 列'{col}'の値'{original[idx]}'は数値でないためNaNに変換"
            )
        numeric[out_of_range] = np.nan
        df[col] = numeric
    return df, warnings


def deduplicate_responses(
    df: pd.DataFrame,
) -> Tuple[pd.DataFrame, List[str]]:
    """同じ氏名×同じ条件の回答が複数ある場合、最新のものだけ残して警告を返す。
    df には norm_name, condition, timestamp 列が必要。
    """
    warnings: List[str] = []
    # NaT を先頭（最古扱い）に置いてから昇順ソートし、keep="last" で最新を残す
    df = df.sort_values("timestamp", ascending=True, na_position="first")
    duplicates = df.duplicated(subset=["norm_name", "condition"], keep=False)
    if duplicates.any():
        dup_groups = df[duplicates].groupby(["norm_name", "condition"])
        for (name, cond), group in dup_groups:
            latest = group["timestamp"].dropna().max()
            latest_str = str(latest) if pd.notna(latest) else "不明（タイムスタンプ解析不可）"
            warnings.append(
                f"重複: '{name}' の条件'{cond}'に{len(group)}件の回答があります。"
                f"最新（{latest_str}）を使用します。"
            )
    df = df.sort_values("timestamp", ascending=True, na_position="first").drop_duplicates(
        subset=["norm_name", "condition"], keep="last"
    )
    return df.reset_index(drop=True), warnings


def match_pairs(
    df: pd.DataFrame,
) -> Tuple[pd.DataFrame, List[Dict], List[str]]:
    """各氏名に条件A・条件Bの両方があるかを確認する。
    片方しかない人は比較分析から除外し、excludedリストに記録する。
    返り値: (ペアが揃った行のdf, excluded[{name, reason}], warnings)
    """
    warnings: List[str] = []
    excluded: List[Dict] = []

    names_with_a = set(df[df["condition"] == config.CONDITION_A]["norm_name"].unique())
    names_with_b = set(df[df["condition"] == config.CONDITION_B]["norm_name"].unique())
    all_names = names_with_a | names_with_b
    paired_names = names_with_a & names_with_b
    unpaired_names = all_names - paired_names

    for name in unpaired_names:
        if name in names_with_a:
            reason = f"条件B の回答が見つかりません（条件A のみ）"
        else:
            reason = f"条件A の回答が見つかりません（条件B のみ）"
        excluded.append({"name": name, "reason": reason})

    paired_df = df[df["norm_name"].isin(paired_names)].copy()
    return paired_df.reset_index(drop=True), excluded, warnings


def assign_group(df: pd.DataFrame) -> pd.DataFrame:
    """グループを判定してdf に group 列（1 or 2 or None）を追加する。
    条件Aを1回目と答えた人 = グループ1, 条件Bを1回目と答えた人 = グループ2。
    group は人単位で全行に同じ値を設定する。
    """
    df = df.copy()
    df["group"] = None

    for name in df["norm_name"].unique():
        person = df[df["norm_name"] == name]
        a_rows = person[person["condition"] == config.CONDITION_A]
        b_rows = person[person["condition"] == config.CONDITION_B]

        a_round = a_rows["round"].iloc[0] if len(a_rows) > 0 else None
        b_round = b_rows["round"].iloc[0] if len(b_rows) > 0 else None

        if a_round == config.ROUND_FIRST:
            group = 1
        elif b_round == config.ROUND_FIRST:
            group = 2
        else:
            group = None

        df.loc[df["norm_name"] == name, "group"] = group

    return df


def detect_round_inconsistency(df: pd.DataFrame) -> List[Tuple[str, str]]:
    """同じ人の2回答で回数が矛盾している（両方1回目など）場合に
    (name, 警告メッセージ) のタプルリストを返す。
    """
    warnings: List[Tuple[str, str]] = []
    for name in df["norm_name"].unique():
        person = df[df["norm_name"] == name]
        rounds = person["round"].dropna().tolist()
        if len(rounds) < 2:
            continue
        if len(set(rounds)) == 1:
            msg = (
                f"'{name}': 2回答の回数が矛盾しています（どちらも{rounds[0]}）。"
                "順番を使う分析からこの人を除外します。"
            )
            warnings.append((name, msg))
    return warnings


def apply_name_aliases(df: pd.DataFrame, aliases_path: str) -> pd.DataFrame:
    """name_aliases.csv（列: alias,name）があれば norm_name に適用する。
    aliases_path が存在しない場合は何もしない。
    """
    import os
    if not os.path.exists(aliases_path):
        return df
    aliases = pd.read_csv(aliases_path)
    alias_map: Dict[str, str] = {}
    for _, row in aliases.iterrows():
        alias_norm = normalize_name(str(row["alias"]))
        name_norm = normalize_name(str(row["name"]))
        alias_map[alias_norm] = name_norm
    df = df.copy()
    df["norm_name"] = df["norm_name"].map(lambda n: alias_map.get(n, n))
    return df


def assign_participant_ids(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """norm_name を参加者ID（P01, P02...）に変換し、norm_name 列を上書きする。

    最初のタイムスタンプ順（NaT は最後）でIDを割り当てる。
    Returns: (更新済み df, {participant_id: 元の norm_name} の辞書)
    """
    first_ts = (
        df.groupby("norm_name")["timestamp"]
        .min()
        .sort_values(na_position="last")
    )
    sorted_names = first_ts.index.tolist()
    name_to_id: Dict[str, str] = {name: f"P{i + 1:02d}" for i, name in enumerate(sorted_names)}
    id_to_name: Dict[str, str] = {pid: name for name, pid in name_to_id.items()}

    df = df.copy()
    df["norm_name"] = df["norm_name"].map(name_to_id)
    return df, id_to_name


def load_responses(
    source: Union[str, IO],
    aliases_path: str = "",
) -> Tuple[pd.DataFrame, List[str]]:
    """CSVを読み込み、前処理を行って (df, warnings) を返す。

    返すdfの列名は config.COLUMN_MAP のキー（内部名）。
    追加列: norm_name, group
    """
    all_warnings: List[str] = []

    # ── CSV 読み込み（エンコード自動判定） ─────────────────────────────────────
    if isinstance(source, str):
        df, enc = _read_csv_auto_encoding(source)
        if enc != "utf-8-sig":
            all_warnings.append(
                f"[文字コード] {enc} で読み込みました。"
                "フォームからダウンロードしたCSVは UTF-8 推奨です。"
            )
    else:
        df = pd.read_csv(source, encoding="utf-8-sig")

    # 列名をリネーム
    df, w = _rename_columns(df)
    all_warnings.extend(w)

    # ── タイムスタンプ解析（午前/午後 形式を含む） ───────────────────────────────
    df["timestamp"] = df["timestamp"].apply(
        lambda x: parse_timestamp(str(x)) if pd.notna(x) else pd.NaT
    )
    nat_count = df["timestamp"].isna().sum()
    if nat_count > 0:
        all_warnings.append(
            f"[タイムスタンプ] {nat_count} 件のタイムスタンプを解析できませんでした（NaT）。"
            "重複判定に影響する可能性があります。"
        )

    # 氏名の正規化（NaN はそのまま渡して "" を返させる）
    df["norm_name"] = df["name"].apply(normalize_name)

    # ── 空欄氏名を除外 ───────────────────────────────────────────────────────────
    blank_count = (df["norm_name"] == "").sum()
    if blank_count > 0:
        all_warnings.append(
            f"氏名が空欄の回答 {blank_count} 件を除外しました。"
        )
        df = df[df["norm_name"] != ""].copy()

    # エイリアス適用
    if aliases_path:
        df = apply_name_aliases(df, aliases_path)

    # スケール値の検証
    df, w = _validate_scale(df)
    all_warnings.extend(w)

    # 違和感・興味の選択肢の検証
    df, w = _validate_discomfort(df)
    all_warnings.extend(w)

    return df, all_warnings
