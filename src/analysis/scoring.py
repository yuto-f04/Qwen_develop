"""src/analysis/scoring.py — エンタメ体験得点と Cronbach's α"""
from typing import Tuple

import numpy as np
import pandas as pd

from src import config


def compute_entertainment_score(df: pd.DataFrame) -> pd.Series:
    """interest・recommend・satisfaction・revisit の平均をエンタメ体験得点として返す。
    いずれかが NaN なら NaN を返す（NaN伝播）。
    """
    items = config.ENTERTAINMENT_ITEMS
    return df[items].mean(axis=1, skipna=False)


def cronbach_alpha(df: pd.DataFrame) -> float:
    """Cronbach's α を計算する。
    df の各列が1項目に対応し、行が被験者。
    被験者が2人未満、または合計点の分散が0（全員同点）の場合は NaN を返す。
    """
    n = len(df)
    if n < 2:
        return np.nan
    k = len(df.columns)
    if k < 2:
        return np.nan
    item_vars = df.var(axis=0, ddof=1)
    total_var = df.sum(axis=1).var(ddof=1)
    if total_var == 0:
        return np.nan  # 全員が同じ合計点のため計算不能
    alpha = (k / (k - 1)) * (1 - item_vars.sum() / total_var)
    return float(alpha)


def select_primary_metric(alpha_a: float, alpha_b: float) -> Tuple[str, str]:
    """α が両方しきい値以上なら entertainment_score、そうでなければ satisfaction を返す。
    NaN（計算不能）・負の値は「しきい値未満」として扱う。
    Returns: (metric_name, note)
    """
    threshold = config.CRONBACH_ALPHA_THRESHOLD

    def _meets(a: float) -> bool:
        """NaN・負は threshold 未満と同等に扱う"""
        if np.isnan(a):
            return False
        return a >= threshold

    if _meets(alpha_a) and _meets(alpha_b):
        return "entertainment_score", ""

    a_str = "計算不能" if np.isnan(alpha_a) else f"{alpha_a:.3f}"
    b_str = "計算不能" if np.isnan(alpha_b) else f"{alpha_b:.3f}"

    if np.isnan(alpha_a) or np.isnan(alpha_b):
        note = (
            f"全員が同じ点のため α を計算できず、満足度を主指標とした"
            f"（条件A: {a_str}、条件B: {b_str}）。"
        )
    else:
        note = (
            f"Cronbach's α が条件A={a_str}、条件B={b_str} のうち一方または両方が"
            f"しきい値 {threshold} を下回ったため、主指標を satisfaction（満足度1項目）に切り替えました。"
        )
    return "satisfaction", note
