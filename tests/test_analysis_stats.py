"""tests/test_analysis_stats.py — stats_tests.py の単体テスト (TDD)"""
import numpy as np
import pytest
from scipy import stats

from src.analysis.stats_tests import (
    wilcoxon_signed_rank,
    mann_whitney_u,
    cliffs_delta,
    mean_ci_95,
    bootstrap_median_ci,
    cohens_dz,
    effect_r_from_z,
)


# ──────────────────────────────────────────────────────────────────────────────
# effect_r_from_z
# ──────────────────────────────────────────────────────────────────────────────

class TestEffectRFromZ:
    def test_basic(self):
        r = effect_r_from_z(z=2.0, n=16)
        assert r == pytest.approx(2.0 / 4.0)

    def test_absolute_value(self):
        r_pos = effect_r_from_z(z=2.0, n=16)
        r_neg = effect_r_from_z(z=-2.0, n=16)
        assert r_pos == r_neg


# ──────────────────────────────────────────────────────────────────────────────
# cohens_dz
# ──────────────────────────────────────────────────────────────────────────────

class TestCohensDz:
    def test_basic(self):
        diffs = np.array([1.0, 2.0, 3.0, 4.0])
        dz = cohens_dz(diffs)
        assert dz == pytest.approx(np.mean(diffs) / np.std(diffs, ddof=1))

    def test_zero_sd_returns_nan(self):
        diffs = np.array([3.0, 3.0, 3.0])
        dz = cohens_dz(diffs)
        assert np.isnan(dz)


# ──────────────────────────────────────────────────────────────────────────────
# mean_ci_95
# ──────────────────────────────────────────────────────────────────────────────

class TestMeanCI95:
    def test_returns_tuple_of_two(self):
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        ci = mean_ci_95(data)
        assert len(ci) == 2
        assert ci[0] < ci[1]

    def test_contains_true_mean(self):
        rng = np.random.default_rng(0)
        data = rng.normal(loc=5.0, scale=1.0, size=100)
        lo, hi = mean_ci_95(data)
        assert lo < 5.0 < hi


# ──────────────────────────────────────────────────────────────────────────────
# bootstrap_median_ci
# ──────────────────────────────────────────────────────────────────────────────

class TestBootstrapMedianCI:
    def test_returns_tuple_of_two(self):
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
        lo, hi = bootstrap_median_ci(data, n=1000, seed=42)
        assert lo < hi

    def test_seed_reproducibility(self):
        data = np.array([1.0, 3.0, 5.0, 7.0, 2.0, 4.0])
        r1 = bootstrap_median_ci(data, n=500, seed=0)
        r2 = bootstrap_median_ci(data, n=500, seed=0)
        assert r1 == r2


# ──────────────────────────────────────────────────────────────────────────────
# wilcoxon_signed_rank
# ──────────────────────────────────────────────────────────────────────────────

class TestWilcoxonSignedRank:
    def _make_pairs(self, a_vals, b_vals):
        return np.array(a_vals, dtype=float), np.array(b_vals, dtype=float)

    def test_basic_result_fields(self):
        a = np.array([3.0, 4.0, 5.0, 6.0, 7.0, 8.0])
        b = np.array([5.0, 6.0, 7.0, 8.0, 9.0, 10.0])
        result = wilcoxon_signed_rank(a, b)
        for key in ["n_used", "n_tied", "W", "p", "r", "dz", "mean_diff",
                    "median_diff", "sd_diff", "ci_mean", "ci_median"]:
            assert key in result, f"キー '{key}' が結果に含まれていない"

    def test_ties_excluded(self):
        a = np.array([5.0, 5.0, 3.0, 4.0])
        b = np.array([5.0, 5.0, 7.0, 8.0])
        result = wilcoxon_signed_rank(a, b)
        assert result["n_tied"] == 2
        assert result["n_used"] == 2

    def test_r_matches_formula(self):
        a = np.array([3.0, 4.0, 5.0, 6.0])
        b = np.array([5.0, 6.0, 7.0, 8.0])
        result = wilcoxon_signed_rank(a, b)
        n = result["n_used"]
        expected_r = abs(result["z_stat"]) / np.sqrt(n)
        assert result["r"] == pytest.approx(expected_r, abs=1e-6)

    def test_p_matches_scipy(self):
        a = np.array([3.0, 4.0, 5.0, 6.0, 5.5, 4.5])
        b = np.array([5.0, 6.0, 7.0, 8.0, 7.5, 6.5])
        result = wilcoxon_signed_rank(a, b)
        diffs = b - a
        nonzero = diffs[diffs != 0]
        scipy_result = stats.wilcoxon(nonzero, zero_method="wilcox", alternative="two-sided")
        assert result["p"] == pytest.approx(scipy_result.pvalue, rel=1e-4)

    def test_dz_formula(self):
        # diffs が同じ値にならないよう b をずらす
        a = np.array([3.0, 4.0, 5.0, 6.0])
        b = np.array([5.0, 7.0, 6.0, 9.0])
        result = wilcoxon_signed_rank(a, b)
        diffs = b - a
        expected_dz = np.mean(diffs) / np.std(diffs, ddof=1)
        assert result["dz"] == pytest.approx(expected_dz, abs=1e-6)

    def test_all_tied_returns_nan(self):
        a = np.array([5.0, 5.0, 5.0])
        b = np.array([5.0, 5.0, 5.0])
        result = wilcoxon_signed_rank(a, b)
        assert np.isnan(result["p"])
        assert result["n_used"] == 0


# ──────────────────────────────────────────────────────────────────────────────
# mann_whitney_u
# ──────────────────────────────────────────────────────────────────────────────

class TestMannWhitneyU:
    def test_basic_result_fields(self):
        x = np.array([1.0, 2.0, 3.0])
        y = np.array([4.0, 5.0, 6.0])
        result = mann_whitney_u(x, y)
        for key in ["U", "p", "r", "delta"]:
            assert key in result

    def test_r_formula(self):
        x = np.array([1.0, 2.0, 3.0])
        y = np.array([4.0, 5.0, 6.0])
        result = mann_whitney_u(x, y)
        n = len(x) + len(y)
        expected_r = abs(result["z_stat"]) / np.sqrt(n)
        assert result["r"] == pytest.approx(expected_r, abs=1e-6)

    def test_p_matches_scipy(self):
        x = np.array([1.0, 2.0, 3.0, 4.0])
        y = np.array([3.0, 5.0, 7.0, 9.0])
        result = mann_whitney_u(x, y)
        scipy_result = stats.mannwhitneyu(x, y, alternative="two-sided")
        assert result["p"] == pytest.approx(scipy_result.pvalue, rel=1e-4)


# ──────────────────────────────────────────────────────────────────────────────
# cliffs_delta
# ──────────────────────────────────────────────────────────────────────────────

class TestCliffsDelta:
    def test_all_x_greater(self):
        x = np.array([1.0, 2.0, 3.0])
        y = np.array([4.0, 5.0, 6.0])
        delta = cliffs_delta(x, y)
        # x すべてが y より小さいので delta = -1
        assert delta == pytest.approx(-1.0)

    def test_all_y_greater(self):
        x = np.array([4.0, 5.0, 6.0])
        y = np.array([1.0, 2.0, 3.0])
        delta = cliffs_delta(x, y)
        assert delta == pytest.approx(1.0)

    def test_identical_returns_zero(self):
        x = np.array([3.0, 3.0, 3.0])
        y = np.array([3.0, 3.0, 3.0])
        delta = cliffs_delta(x, y)
        assert delta == pytest.approx(0.0)

    def test_range_minus1_to_1(self):
        rng = np.random.default_rng(1)
        x = rng.integers(1, 11, size=10).astype(float)
        y = rng.integers(1, 11, size=10).astype(float)
        delta = cliffs_delta(x, y)
        assert -1.0 <= delta <= 1.0


# ──────────────────────────────────────────────────────────────────────────────
# I1: mann_whitney_u の呼び出し側で Cliff's δ が「B>Aで正」になること
# stats_tests.py 自体は cliffs_delta(x, y) の汎用関数のまま。
# report.py が grp2_B を第1引数、grp1_A を第2引数で渡すことを
# ここでは「仕様コメントとして」確認し、report のテストで結果の符号を検証する。
# ──────────────────────────────────────────────────────────────────────────────

class TestMannWhitneyUDirectionConvention:
    """mann_whitney_u(b_vals, a_vals) のとき delta > 0 ↔ B > A の確認"""

    def test_b_greater_than_a_gives_positive_delta(self):
        b_vals = np.array([7.0, 8.0, 9.0])   # B 側が大きい
        a_vals = np.array([4.0, 5.0, 6.0])   # A 側が小さい
        result = mann_whitney_u(b_vals, a_vals)
        assert result["delta"] > 0, "B>A のとき delta は正であること"

    def test_a_greater_than_b_gives_negative_delta(self):
        b_vals = np.array([4.0, 5.0, 6.0])
        a_vals = np.array([7.0, 8.0, 9.0])
        result = mann_whitney_u(b_vals, a_vals)
        assert result["delta"] < 0, "A>B のとき delta は負であること"
