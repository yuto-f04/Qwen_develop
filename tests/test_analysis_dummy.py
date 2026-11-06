"""tests/test_analysis_dummy.py — dummy.py の単体テスト (TDD)"""
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from src import config
from src.analysis.dummy import generate_dummy_csv


N_PEOPLE = 20       # デフォルトは 10×2 グループ
N_ROWS   = N_PEOPLE * 2   # 1人2回答


class TestGenerateDummyCsv:
    def setup_method(self):
        self.df = generate_dummy_csv()

    def test_row_count(self):
        assert len(self.df) == N_ROWS

    def test_all_columns_present(self):
        for col in config.COLUMN_MAP.values():
            assert col in self.df.columns, f"列 '{col}' が見つかりません"

    def test_each_person_has_both_conditions(self):
        name_col = config.COLUMN_MAP["name"]
        cond_col = config.COLUMN_MAP["condition"]
        for name, group in self.df.groupby(name_col):
            conds = set(group[cond_col])
            assert conds == {config.CONDITION_A, config.CONDITION_B}, \
                f"{name} の条件が {conds}"

    def test_each_person_has_both_rounds(self):
        name_col = config.COLUMN_MAP["name"]
        round_col = config.COLUMN_MAP["round"]
        for name, group in self.df.groupby(name_col):
            rounds = set(group[round_col])
            assert rounds == {config.ROUND_FIRST, config.ROUND_SECOND}, \
                f"{name} の回数が {rounds}"

    def test_scale_values_in_range(self):
        for key in config.SCALE_ITEMS:
            col = config.COLUMN_MAP[key]
            vals = pd.to_numeric(self.df[col])
            assert (vals >= 1).all() and (vals <= 10).all(), \
                f"列 '{col}' に範囲外の値があります"

    def test_condition_values_valid(self):
        cond_col = config.COLUMN_MAP["condition"]
        valid = {config.CONDITION_A, config.CONDITION_B}
        assert set(self.df[cond_col].unique()).issubset(valid)

    def test_round_values_valid(self):
        round_col = config.COLUMN_MAP["round"]
        valid = {config.ROUND_FIRST, config.ROUND_SECOND}
        assert set(self.df[round_col].unique()).issubset(valid)

    def test_discomfort_values_valid(self):
        disc_col = config.COLUMN_MAP["discomfort"]
        valid = set(config.DISCOMFORT_CATEGORIES)
        assert set(self.df[disc_col].unique()).issubset(valid)

    def test_discomfort_interest_valid(self):
        """違和感あり行の discomfort_interest は既知の選択肢"""
        disc_col = config.COLUMN_MAP["discomfort"]
        interest_col = config.COLUMN_MAP["discomfort_interest"]
        disc_rows = self.df[self.df[disc_col].isin(config.DISCOMFORT_PRESENT_CATEGORIES)]
        valid = set(config.DISCOMFORT_INTEREST_CHOICES)
        for val in disc_rows[interest_col].dropna():
            assert val in valid or val == "", f"想定外の値: {val}"

    def test_groups_balanced(self):
        """グループ1(A先行)とグループ2(B先行)が均等に存在すること"""
        name_col  = config.COLUMN_MAP["name"]
        cond_col  = config.COLUMN_MAP["condition"]
        round_col = config.COLUMN_MAP["round"]
        a_first_count = 0
        b_first_count = 0
        for name, group in self.df.groupby(name_col):
            first = group[group[round_col] == config.ROUND_FIRST]
            if len(first) == 0:
                continue
            if first[cond_col].iloc[0] == config.CONDITION_A:
                a_first_count += 1
            else:
                b_first_count += 1
        assert a_first_count == 10
        assert b_first_count == 10

    def test_seed_reproducibility(self):
        df2 = generate_dummy_csv(seed=42)
        name_col = config.COLUMN_MAP["name"]
        pd.testing.assert_frame_equal(self.df, df2)

    def test_different_seeds_differ(self):
        df2 = generate_dummy_csv(seed=99)
        # スケール値が全て同じになることはない
        for key in config.SCALE_ITEMS[:3]:
            col = config.COLUMN_MAP[key]
            if not (self.df[col].values == df2[col].values).all():
                return
        pytest.fail("異なるシードなのに全列が同一です")

    def test_no_names_in_other_outputs(self):
        """ダミーデータの氏名はCSV列だけに存在し、匿名化後に消えること"""
        name_col = config.COLUMN_MAP["name"]
        names = set(self.df[name_col].unique())
        # 他の列にそのまま氏名が漏れていないことの確認
        for col in self.df.columns:
            if col == name_col:
                continue
            vals = self.df[col].astype(str)
            for name in names:
                assert not vals.str.contains(name, regex=False).any(), \
                    f"列 '{col}' に氏名 '{name}' が含まれています"


class TestFullAnalysisOnDummy:
    """ダミーデータで全分析が最後まで動くことを確認するインテグレーションテスト"""

    def test_run_analysis_completes(self, tmp_path):
        from src.analysis.report import run_analysis

        df = generate_dummy_csv(seed=42)
        csv_path = str(tmp_path / "dummy.csv")
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")

        results, notes = run_analysis(csv_path, str(tmp_path / "output"))

        assert results["n_paired"] == 20
        assert results["group_counts"].get(1, 0) == 10
        assert results["group_counts"].get(2, 0) == 10
        assert "main_result" in results
        assert results["main_result"]["n_used"] > 0

    def test_output_files_created(self, tmp_path):
        from src.analysis.report import run_analysis

        df = generate_dummy_csv(seed=42)
        csv_path = str(tmp_path / "dummy.csv")
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        outdir = tmp_path / "output"

        run_analysis(csv_path, str(outdir))

        for fname in ["report.md", "wide.csv", "tidy.csv",
                      "free_text.csv", "participant_map.csv"]:
            assert (outdir / fname).exists(), f"{fname} が出力されていません"

    def test_output_no_real_names(self, tmp_path):
        """wide.csv / tidy.csv に氏名が残っていないこと"""
        from src.analysis.report import run_analysis

        df = generate_dummy_csv(seed=42)
        name_col = config.COLUMN_MAP["name"]
        real_names = set(df[name_col].unique())

        csv_path = str(tmp_path / "dummy.csv")
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        outdir = tmp_path / "output"
        run_analysis(csv_path, str(outdir))

        for fname in ["wide.csv", "tidy.csv"]:
            content = (outdir / fname).read_text(encoding="utf-8-sig")
            for name in real_names:
                assert name not in content, \
                    f"{fname} に氏名 '{name}' が残っています"
