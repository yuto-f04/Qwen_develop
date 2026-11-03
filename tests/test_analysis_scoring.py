"""tests/test_analysis_scoring.py — scoring.py の単体テスト (TDD)"""
import numpy as np
import pandas as pd
import pytest

from src.analysis.scoring import (
    compute_entertainment_score,
    cronbach_alpha,
    select_primary_metric,
)


class TestComputeEntertainmentScore:
    def test_mean_of_four_items(self):
        df = pd.DataFrame({
            "interest": [8], "recommend": [6], "satisfaction": [7], "revisit": [5],
        })
        result = compute_entertainment_score(df)
        assert result.iloc[0] == pytest.approx((8 + 6 + 7 + 5) / 4)

    def test_nan_propagation(self):
        df = pd.DataFrame({
            "interest": [np.nan], "recommend": [6], "satisfaction": [7], "revisit": [5],
        })
        result = compute_entertainment_score(df)
        assert np.isnan(result.iloc[0])

    def test_multiple_rows(self):
        df = pd.DataFrame({
            "interest":      [8, 4],
            "recommend":     [6, 6],
            "satisfaction":  [7, 5],
            "revisit":       [9, 3],
        })
        result = compute_entertainment_score(df)
        assert result.iloc[0] == pytest.approx(30 / 4)
        assert result.iloc[1] == pytest.approx(18 / 4)


class TestCronbachAlpha:
    def test_perfect_correlation_returns_1(self):
        # 全列が同じ値なら α = 1
        data = np.array([[1, 1, 1, 1],
                         [2, 2, 2, 2],
                         [3, 3, 3, 3],
                         [4, 4, 4, 4],
                         [5, 5, 5, 5]], dtype=float)
        df = pd.DataFrame(data, columns=["a", "b", "c", "d"])
        alpha = cronbach_alpha(df)
        assert alpha == pytest.approx(1.0)

    def test_known_value(self):
        # 手計算で確認できる小さな例
        # 3項目 × 4人
        # item1: [1, 2, 3, 4]  var=1.25
        # item2: [2, 4, 6, 8]  var=5.0
        # item3: [1, 1, 3, 3]  var=1.0
        # total: [4, 7, 12, 15] var=18.25  （不偏分散 ×(n-1)/n で補正しない場合）
        # Cronbach α = k/(k-1) * (1 - Σvar_i / var_total)
        # 標本分散（ddof=1）:
        # var1=5/3, var2=20/3, var3=4/3, var_total=...
        data = {
            "item1": [1, 2, 3, 4],
            "item2": [2, 4, 6, 8],
            "item3": [1, 1, 3, 3],
        }
        df = pd.DataFrame(data, dtype=float)
        alpha = cronbach_alpha(df)
        # 手計算: var_total = np.var([4,7,12,15], ddof=1) = 26.25
        # Σvar_i = 5/3 + 20/3 + 4/3 = 29/3 ≈ 9.667
        # α = 3/2 * (1 - 9.667 / 26.25) ≈ 3/2 * (1 - 0.3683) ≈ 0.947
        assert alpha == pytest.approx(
            3 / 2 * (1 - (5/3 + 20/3 + 4/3) / np.var([4, 7, 12, 15], ddof=1)),
            abs=1e-10
        )

    def test_small_sample_returns_nan_not_crash(self):
        # 1行以下のデータでは計算不能
        df = pd.DataFrame({"a": [5.0], "b": [6.0]})
        alpha = cronbach_alpha(df)
        assert np.isnan(alpha)


class TestSelectPrimaryMetric:
    def test_both_high_returns_entertainment(self):
        metric, note = select_primary_metric(alpha_a=0.80, alpha_b=0.75)
        assert metric == "entertainment_score"
        assert note == ""

    def test_a_low_returns_satisfaction(self):
        metric, note = select_primary_metric(alpha_a=0.65, alpha_b=0.80)
        assert metric == "satisfaction"
        assert "satisfaction" in note.lower() or "満足" in note

    def test_b_low_returns_satisfaction(self):
        metric, note = select_primary_metric(alpha_a=0.80, alpha_b=0.60)
        assert metric == "satisfaction"

    def test_both_low_returns_satisfaction(self):
        metric, note = select_primary_metric(alpha_a=0.50, alpha_b=0.50)
        assert metric == "satisfaction"

    def test_exactly_threshold_returns_entertainment(self):
        metric, _ = select_primary_metric(alpha_a=0.70, alpha_b=0.70)
        assert metric == "entertainment_score"
