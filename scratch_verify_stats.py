"""独立した統計再計算スクリプト（プロジェクトコードを import しない）
点検3: ダミーデータの数値を手計算して report.md と照合する。
"""
import numpy as np
from scipy import stats

# ── ダミーデータのsatisfaction値（ダミーCSVをシード42で生成したもの）
# run_analysis の output/analysis/wide.csv から取得した値を使う
# ここでは make_dummy_data の乱数を再現して得る

import numpy as np
import pandas as pd
from pathlib import Path

wide = pd.read_csv("output/analysis/wide.csv", encoding="utf-8-sig")
a_vals = wide["satisfaction_A"].dropna().values
b_vals = wide["satisfaction_B"].dropna().values
diffs = b_vals - a_vals

print("=== 独立統計再計算 ===")
print(f"全ペア数: {len(diffs)}")

# 同点を除く
nonzero = diffs[diffs != 0]
n_tied = int(np.sum(diffs == 0))
n_used = len(nonzero)
print(f"同点: {n_tied}, 使用: {n_used}")

# Wilcoxon W と p（scipy）
scipy_result = stats.wilcoxon(nonzero, zero_method="wilcox", alternative="two-sided")
W = scipy_result.statistic
p = scipy_result.pvalue
print(f"\nwilcoxon: W={W:.3f}, p={p:.4f}")
print(f"report.md: W=19.000, p=0.011")
print(f"W一致: {abs(W - 19.0) < 0.001}, p近似: {abs(p - 0.011) < 0.002}")

# Z統計量（正規近似）
try:
    z = float(scipy_result.zstatistic)
    print(f"zstatistic (scipy): {z:.4f}")
except AttributeError:
    mu_W = n_used * (n_used + 1) / 4
    sigma_W = np.sqrt(n_used * (n_used + 1) * (2 * n_used + 1) / 24)
    z = (W - mu_W) / sigma_W
    print(f"zstatistic (手計算): {z:.4f}")

# r = |Z|/√N（N=n_used）
r = abs(z) / np.sqrt(n_used)
print(f"r = |Z|/√N = {abs(z):.4f}/√{n_used} = {r:.4f}")
print(f"report.md: r=0.633, 一致: {abs(r - 0.633) < 0.005}")

# Cohen's dz（全差を使う）
mean_d = np.mean(diffs)
sd_d = np.std(diffs, ddof=1)
dz = mean_d / sd_d
print(f"\ndz = {mean_d:.4f}/{sd_d:.4f} = {dz:.4f}")
print(f"report.md: dz=0.671, 一致: {abs(dz - 0.671) < 0.005}")

# 差の平均の95%CI（t分布）
n_all = len(diffs)
se = sd_d / np.sqrt(n_all)
t_crit = stats.t.ppf(0.975, df=n_all - 1)
ci_lo = mean_d - t_crit * se
ci_hi = mean_d + t_crit * se
print(f"\nCI_mean: [{ci_lo:.3f}, {ci_hi:.3f}]")
print(f"report.md: [0.453, 2.547]")

# ブートストラップ中央値CI
rng2 = np.random.default_rng(42)
medians = [np.median(rng2.choice(diffs, size=len(diffs), replace=True)) for _ in range(5000)]
boot_lo = np.percentile(medians, 2.5)
boot_hi = np.percentile(medians, 97.5)
print(f"\nBootstrap CI: [{boot_lo:.3f}, {boot_hi:.3f}]")
print(f"report.md: [0.000, 3.000]")

# Cronbach's α（手計算）
print("\n=== Cronbach's α 手計算 ===")
data = {"item1": [1., 2., 3., 4.], "item2": [2., 4., 6., 8.], "item3": [1., 1., 3., 3.]}
df3 = pd.DataFrame(data)
k = 3
item_vars = df3.var(ddof=1)
total_var = df3.sum(axis=1).var(ddof=1)
alpha_hand = (k / (k - 1)) * (1 - item_vars.sum() / total_var)
print(f"手計算α: {alpha_hand:.6f}")
expected = 3/2 * (1 - (5/3 + 20/3 + 4/3) / np.var([4, 7, 12, 15], ddof=1))
print(f"期待値α: {expected:.6f}")
print(f"一致: {abs(alpha_hand - expected) < 1e-8}")

# Holm補正（手計算）
print("\n=== Holm補正 ===")
pvals = [0.007, 0.026, 0.011, 0.003, 0.529]
k_h = len(pvals)
indexed = sorted(enumerate(pvals), key=lambda x: x[1])
corrected = [None] * k_h
prev_p = 0.0
for rank, (orig_idx, p_h) in enumerate(indexed):
    adj = min(1.0, max(prev_p, p_h * (k_h - rank)))
    corrected[orig_idx] = adj
    prev_p = adj
print(f"Holm補正後: {[f'{v:.4f}' for v in corrected]}")
print(f"report.md: [0.027, 0.052, 0.032, 0.014, 0.529]")

# Mann-Whitney（1回目比較）
print("\n=== 1回目だけの比較（Mann-Whitney）===")
g1 = wide[wide["group"] == 1]["satisfaction_A"].dropna().values
g2 = wide[wide["group"] == 2]["satisfaction_B"].dropna().values
mw = stats.mannwhitneyu(g1, g2, alternative="two-sided")
U_mw = mw.statistic
p_mw = mw.pvalue
n1, n2 = len(g1), len(g2)
mu_U = n1 * n2 / 2
sigma_U = np.sqrt(n1 * n2 * (n1 + n2 + 1) / 12)
z_mw = (U_mw - mu_U) / sigma_U
r_mw = abs(z_mw) / np.sqrt(n1 + n2)
print(f"U={U_mw:.3f}, p={p_mw:.4f}, r={r_mw:.3f}")
print(f"report.md: U=9.000, p=0.002, r=0.693")
# Cliff's delta
greater = sum(xi > yj for xi in g1 for yj in g2)
less = sum(xi < yj for xi in g1 for yj in g2)
delta = (greater - less) / (n1 * n2)
print(f"Cliff's δ (g1 vs g2) = {delta:.4f}")
print(f"report.md: δ=-0.820")
print(f"(負の値はg2の条件Bの方が高いことを示す。向きの説明がレポートにない)")
