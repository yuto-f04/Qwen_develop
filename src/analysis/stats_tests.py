"""src/analysis/stats_tests.py — 検定・効果量・信頼区間"""
from typing import Dict, Any, Tuple

import numpy as np
from scipy import stats

from src import config


def effect_r_from_z(z: float, n: int) -> float:
    """効果量 r = |Z| / √N"""
    return abs(z) / np.sqrt(n)


def cohens_dz(diffs: np.ndarray) -> float:
    """Cohen's dz = 差の平均 / 差のSD（ddof=1）"""
    sd = np.std(diffs, ddof=1)
    if sd == 0:
        return np.nan
    return float(np.mean(diffs) / sd)


def mean_ci_95(data: np.ndarray) -> Tuple[float, float]:
    """差の平均の95%信頼区間（t分布）"""
    n = len(data)
    se = np.std(data, ddof=1) / np.sqrt(n)
    t_crit = stats.t.ppf(0.975, df=n - 1)
    mean = np.mean(data)
    return float(mean - t_crit * se), float(mean + t_crit * se)


def bootstrap_median_ci(
    data: np.ndarray, n: int = None, seed: int = None
) -> Tuple[float, float]:
    """中央値のブートストラップ95%信頼区間"""
    if n is None:
        n = config.BOOTSTRAP_N
    if seed is None:
        seed = config.BOOTSTRAP_SEED
    rng = np.random.default_rng(seed)
    medians = np.array([
        np.median(rng.choice(data, size=len(data), replace=True))
        for _ in range(n)
    ])
    lo = float(np.percentile(medians, 2.5))
    hi = float(np.percentile(medians, 97.5))
    return lo, hi


def _compute_z_from_wilcoxon(diffs_nonzero: np.ndarray, W: float) -> float:
    """ウィルコクソン符号順位検定の W 統計量から Z を正規近似で計算する。
    scipy のバージョンによって zstatistic がない場合に備えた自前計算。
    """
    n = len(diffs_nonzero)
    mu_W = n * (n + 1) / 4
    sigma_W = np.sqrt(n * (n + 1) * (2 * n + 1) / 24)
    if sigma_W == 0:
        return np.nan
    return float((W - mu_W) / sigma_W)


def wilcoxon_signed_rank(
    a: np.ndarray, b: np.ndarray
) -> Dict[str, Any]:
    """ウィルコクソンの符号順位検定（条件B - 条件A の差で検定）。

    Returns:
        n_used: 同点を除いた人数
        n_tied: 同点の人数
        W: 統計量
        p: p値
        z_stat: Z 統計量（正規近似）
        r: 効果量 r = |Z|/√N
        dz: Cohen's dz
        mean_diff: B−A の平均
        median_diff: B−A の中央値
        sd_diff: B−A のSD
        ci_mean: 差の平均の95%CI
        ci_median: 差の中央値のブートストラップ95%CI
    """
    diffs = b - a
    n_tied = int(np.sum(diffs == 0))
    diffs_nonzero = diffs[diffs != 0]
    n_used = len(diffs_nonzero)

    result: Dict[str, Any] = {
        "n_used": n_used,
        "n_tied": n_tied,
        "W": np.nan,
        "p": np.nan,
        "z_stat": np.nan,
        "r": np.nan,
        "dz": np.nan,
        "mean_diff": float(np.mean(diffs)),
        "median_diff": float(np.median(diffs)),
        "sd_diff": float(np.std(diffs, ddof=1)) if len(diffs) >= 2 else np.nan,
        "ci_mean": (np.nan, np.nan),
        "ci_median": (np.nan, np.nan),
    }

    if n_used == 0:
        return result

    scipy_result = stats.wilcoxon(
        diffs_nonzero, zero_method="wilcox", alternative="two-sided"
    )
    W = float(scipy_result.statistic)
    p = float(scipy_result.pvalue)

    # Z の計算（scipy バージョンに依存しない）
    try:
        z_stat = float(scipy_result.zstatistic)
    except AttributeError:
        z_stat = _compute_z_from_wilcoxon(diffs_nonzero, W)

    r = effect_r_from_z(z_stat, n_used)
    dz = cohens_dz(diffs)
    ci_mean = mean_ci_95(diffs) if len(diffs) >= 2 else (np.nan, np.nan)
    ci_median = bootstrap_median_ci(diffs) if len(diffs) >= 2 else (np.nan, np.nan)

    result.update({
        "W": W,
        "p": p,
        "z_stat": z_stat,
        "r": r,
        "dz": dz,
        "ci_mean": ci_mean,
        "ci_median": ci_median,
    })
    return result


def mann_whitney_u(x: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
    """マン・ホイットニーのU検定（x: グループ1, y: グループ2）

    Returns: U, p, z_stat, r, delta（Cliff's delta）
    """
    scipy_result = stats.mannwhitneyu(x, y, alternative="two-sided")
    U = float(scipy_result.statistic)
    p = float(scipy_result.pvalue)

    n1, n2 = len(x), len(y)
    n_total = n1 + n2
    mu_U = n1 * n2 / 2
    sigma_U = np.sqrt(n1 * n2 * (n1 + n2 + 1) / 12)
    z_stat = (U - mu_U) / sigma_U if sigma_U > 0 else np.nan
    r = effect_r_from_z(z_stat, n_total)
    delta = cliffs_delta(x, y)

    return {
        "U": U,
        "p": p,
        "z_stat": float(z_stat),
        "r": float(r),
        "delta": delta,
    }


def cliffs_delta(x: np.ndarray, y: np.ndarray) -> float:
    """Cliff's delta: (x が y より大きい回数 - x が y より小さい回数) / (n1 * n2)"""
    n1, n2 = len(x), len(y)
    if n1 == 0 or n2 == 0:
        return np.nan
    greater = sum(xi > yj for xi in x for yj in y)
    less = sum(xi < yj for xi in x for yj in y)
    return float((greater - less) / (n1 * n2))


def spearman_correlation(x: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
    """スピアマン順位相関係数を計算する。n < 3 の場合は NaN を返す。"""
    n = len(x)
    if n < 3:
        return {"rho": np.nan, "p": np.nan, "n": n}
    result = stats.spearmanr(x, y)
    return {
        "rho": float(result.statistic),
        "p": float(result.pvalue),
        "n": n,
    }


def holm_correction(p_values: list) -> list:
    """Holm 法による多重比較補正済み p 値を返す"""
    k = len(p_values)
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    corrected = [None] * k
    prev_p = 0.0
    for rank, (orig_idx, p) in enumerate(indexed):
        adj = min(1.0, max(prev_p, p * (k - rank)))
        corrected[orig_idx] = adj
        prev_p = adj
    return corrected


def judgment_text(
    mean_diff: float, p: float, condition_a_label: str = "条件A", condition_b_label: str = "条件B"
) -> str:
    """p値と差の方向から判定文を返す"""
    alpha = config.ALPHA_LEVEL
    if p < alpha and mean_diff > 0:
        return f"仮説を支持する（{condition_b_label}が{condition_a_label}より有意に高かった）。"
    elif p < alpha and mean_diff < 0:
        return f"仮説を支持する結果は得られなかった（{condition_a_label}のほうが有意に高かった）。"
    else:
        return "仮説を支持する結果は得られなかった。"
