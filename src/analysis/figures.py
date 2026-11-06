"""src/analysis/figures.py — matplotlib による可視化"""
import warnings
from pathlib import Path
from typing import List

import matplotlib
matplotlib.use("Agg")  # 非インタラクティブ backend（GUI不要・テスト環境で必須）

import numpy as np
import pandas as pd

from src import config


def _setup_japanese_font():
    """日本語フォントを設定する。見つからなくても止まらない。"""
    import matplotlib
    import matplotlib.pyplot as plt

    font_candidates = [
        "Yu Gothic", "Yu Gothic UI", "Meiryo",  # Windows
        "Hiragino Sans", "Hiragino Kaku Gothic Pro",  # Mac
        "Noto Sans CJK JP", "IPAexGothic", "IPAGothic",  # Linux
    ]
    from matplotlib import font_manager
    available = {f.name for f in font_manager.fontManager.ttflist}
    for font in font_candidates:
        if font in available:
            matplotlib.rcParams["font.family"] = font
            return
    # フォントが見つからなければ警告だけ出して続行
    warnings.warn(
        "日本語フォントが見つかりませんでした。文字化けする可能性があります。",
        stacklevel=2,
    )


def plot_main_metric(
    wide_df: pd.DataFrame,
    metric: str,
    outdir: Path,
) -> List[Path]:
    """主指標の対応図と箱ひげ図を作成する。"""
    import matplotlib.pyplot as plt

    _setup_japanese_font()
    outdir.mkdir(parents=True, exist_ok=True)
    saved: List[Path] = []

    a_vals = wide_df[f"{metric}_A"].dropna()
    b_vals = wide_df[f"{metric}_B"].dropna()
    paired_df = wide_df[[f"{metric}_A", f"{metric}_B", "group"]].dropna()

    # ── 対応のある図（線で結ぶ） ───────────────────────────────
    fig, ax = plt.subplots(figsize=(5, 5))
    colors = {1: "#2196F3", 2: "#FF5722"}
    for _, row in paired_df.iterrows():
        g = int(row["group"]) if not np.isnan(row["group"]) else 0
        c = colors.get(g, "#9E9E9E")
        ax.plot([0, 1], [row[f"{metric}_A"], row[f"{metric}_B"]],
                "o-", color=c, alpha=0.7, linewidth=1.2, markersize=5)

    import matplotlib.patches as mpatches
    handles = [mpatches.Patch(color=colors[1], label="グループ1（A→B）"),
               mpatches.Patch(color=colors[2], label="グループ2（B→A）")]
    ax.legend(handles=handles, fontsize=9)
    ax.set_xticks([0, 1])
    ax.set_xticklabels([config.CONDITION_A, config.CONDITION_B])
    ax.set_ylabel(metric)
    ax.set_ylim(0, 11)
    ax.set_title(f"主指標（{metric}）の条件別比較")
    fig.tight_layout()
    p = outdir / "fig_main_metric_pairs.png"
    fig.savefig(p, dpi=120)
    plt.close(fig)
    saved.append(p)

    # ── 箱ひげ図 ───────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(4, 5))
    data_box = [
        paired_df[f"{metric}_A"].tolist(),
        paired_df[f"{metric}_B"].tolist(),
    ]
    bp = ax.boxplot(data_box, labels=[config.CONDITION_A, config.CONDITION_B],
                    patch_artist=True)
    bp["boxes"][0].set_facecolor("#BBDEFB")
    bp["boxes"][1].set_facecolor("#FFCCBC")
    ax.set_ylabel(metric)
    ax.set_ylim(0, 11)
    ax.set_title(f"主指標（{metric}）箱ひげ図")
    fig.tight_layout()
    p = outdir / "fig_main_metric_box.png"
    fig.savefig(p, dpi=120)
    plt.close(fig)
    saved.append(p)

    return saved


def plot_item_means(
    tidy_df: pd.DataFrame,
    outdir: Path,
) -> Path:
    """10項目の条件別平均（95%CI付き）横並び棒グラフ"""
    import matplotlib.pyplot as plt
    from scipy import stats as scipy_stats

    _setup_japanese_font()
    outdir.mkdir(parents=True, exist_ok=True)

    all_items = config.SCALE_ITEMS
    item_labels = {
        "interest": "興味", "length": "長さ", "clarity": "分かりやすさ",
        "enthusiasm": "熱意", "recommend": "おすすめ", "expectation": "期待通り",
        "satisfaction": "満足度", "difficulty": "難しさ", "physical": "体力不安",
        "revisit": "再参加",
    }
    group_order = ["エンタメ4項目", "副指標", "条件確認"]
    item_groups = {
        "エンタメ4項目": config.ENTERTAINMENT_ITEMS,
        "副指標": [i for i in config.SECONDARY_ITEMS if i not in config.ENTERTAINMENT_ITEMS],
        "条件確認": config.CONDITION_CHECK_ITEMS,
    }

    ordered_items = []
    for g in group_order:
        ordered_items.extend(item_groups[g])

    x = np.arange(len(ordered_items))
    width = 0.35
    colors = {"条件A": "#2196F3", "条件B": "#FF5722"}

    fig, ax = plt.subplots(figsize=(12, 5))
    for i, cond in enumerate([config.CONDITION_A, config.CONDITION_B]):
        sub = tidy_df[tidy_df["condition"] == cond]
        means, ci_lows, ci_highs = [], [], []
        for item in ordered_items:
            vals = sub[item].dropna().values
            if len(vals) < 2:
                means.append(np.nan)
                ci_lows.append(0)
                ci_highs.append(0)
                continue
            m = np.mean(vals)
            se = scipy_stats.sem(vals)
            t_crit = scipy_stats.t.ppf(0.975, df=len(vals) - 1)
            means.append(m)
            ci_lows.append(t_crit * se)
            ci_highs.append(t_crit * se)
        offset = (i - 0.5) * width
        ax.bar(x + offset, means, width, label=cond,
               color=colors[cond], alpha=0.8,
               yerr=[ci_lows, ci_highs], capsize=3, error_kw={"linewidth": 1})

    ax.set_xticks(x)
    ax.set_xticklabels([item_labels.get(it, it) for it in ordered_items],
                       rotation=30, ha="right", fontsize=9)
    ax.set_ylim(0, 11)
    ax.set_ylabel("平均点")
    ax.set_title("10項目の条件別平均（95%CI）")
    ax.legend()

    # グループ境界線
    boundary = len(item_groups["エンタメ4項目"]) - 0.5
    ax.axvline(x=boundary, color="gray", linestyle="--", linewidth=0.8)
    boundary2 = boundary + len(item_groups["副指標"])
    ax.axvline(x=boundary2, color="gray", linestyle="--", linewidth=0.8)

    fig.tight_layout()
    p = outdir / "fig_item_means.png"
    fig.savefig(p, dpi=120)
    plt.close(fig)
    return p


def plot_discomfort(
    tidy_df: pd.DataFrame,
    outdir: Path,
) -> List[Path]:
    """違和感の条件別積み上げ棒グラフ（全体と1回目だけ）"""
    import matplotlib.pyplot as plt

    _setup_japanese_font()
    outdir.mkdir(parents=True, exist_ok=True)
    saved: List[Path] = []

    categories = ["なかった", "少しあった", "あった"]
    colors_disc = ["#81C784", "#FFD54F", "#E57373"]

    for suffix, subset_label in [("all", "全体"), ("first", "1回目のみ")]:
        if suffix == "first":
            sub = tidy_df[tidy_df["round"] == config.ROUND_FIRST]
        else:
            sub = tidy_df

        conditions = [config.CONDITION_A, config.CONDITION_B]
        data = []
        for cond in conditions:
            cond_sub = sub[sub["condition"] == cond]["discomfort"]
            total = len(cond_sub.dropna())
            row = []
            for cat in categories:
                count = (cond_sub == cat).sum()
                row.append(count / total if total > 0 else 0)
            data.append(row)

        fig, ax = plt.subplots(figsize=(5, 4))
        bottoms = [0.0, 0.0]
        for j, cat in enumerate(categories):
            vals = [data[i][j] for i in range(len(conditions))]
            ax.bar(conditions, vals, bottom=bottoms,
                   label=cat, color=colors_disc[j], alpha=0.85)
            bottoms = [b + v for b, v in zip(bottoms, vals)]

        ax.set_ylabel("割合")
        ax.set_ylim(0, 1.05)
        ax.set_title(f"違和感の条件別割合（{subset_label}）")
        ax.legend(loc="upper right", fontsize=9)
        fig.tight_layout()
        p = outdir / f"fig_discomfort_{suffix}.png"
        fig.savefig(p, dpi=120)
        plt.close(fig)
        saved.append(p)

    return saved
