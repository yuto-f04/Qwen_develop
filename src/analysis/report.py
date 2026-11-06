"""src/analysis/report.py — 分析の実行とレポート生成"""
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from src import config
from src.analysis.load import (
    load_responses,
    deduplicate_responses,
    match_pairs,
    assign_group,
    detect_round_inconsistency,
    apply_name_aliases,
    assign_participant_ids,
)
from src.analysis.scoring import (
    compute_entertainment_score,
    cronbach_alpha,
    select_primary_metric,
)
from src.analysis.stats_tests import (
    wilcoxon_signed_rank,
    mann_whitney_u,
    cliffs_delta,
    holm_correction,
    judgment_text,
    spearman_correlation,
)


def _fmt_p(p: float) -> str:
    if np.isnan(p):
        return "NaN"
    if p < 0.001:
        return "p < .001"
    return f"p = {p:.3f}"


def _fmt_ci(ci: Tuple[float, float]) -> str:
    return f"[{ci[0]:.3f}, {ci[1]:.3f}]"


def _fmt_f(v: float, decimals: int = 3) -> str:
    if np.isnan(v):
        return "NaN"
    return f"{v:.{decimals}f}"


def run_analysis(
    input_csv: str,
    outdir: str,
    aliases_path: str = "",
) -> Tuple[Dict[str, Any], List[str]]:
    """分析全体を実行し、結果辞書と注意書きリストを返す。副作用として各ファイルを書き出す。"""
    outdir_path = Path(outdir)
    outdir_path.mkdir(parents=True, exist_ok=True)
    figs_dir = outdir_path / "figures"
    figs_dir.mkdir(parents=True, exist_ok=True)

    notes: List[str] = []

    # ── データ読み込み ────────────────────────────────────────
    df_raw, load_warnings = load_responses(input_csv, aliases_path=aliases_path)
    for w in load_warnings:
        notes.append(f"[データ読み込み] {w}")

    # ── 重複除去 ──────────────────────────────────────────────
    df_dedup, dup_warnings = deduplicate_responses(df_raw)
    for w in dup_warnings:
        notes.append(f"[重複] {w}")

    # ── ペア突き合わせ ────────────────────────────────────────
    df_paired, excluded, pair_warnings = match_pairs(df_dedup)
    for w in pair_warnings:
        notes.append(f"[突き合わせ] {w}")

    # ── グループ判定 ──────────────────────────────────────────
    df_paired = assign_group(df_paired)

    # ── 氏名 → 参加者ID（P01, P02...）に置き換え ─────────────
    df_paired, id_to_name = assign_participant_ids(df_paired)
    id_map_rows = [{"participant_id": pid, "氏名": name}
                   for pid, name in sorted(id_to_name.items())]
    pd.DataFrame(id_map_rows).to_csv(
        outdir_path / "participant_map.csv", index=False, encoding="utf-8-sig"
    )

    # ── 回数の矛盾検出 ────────────────────────────────────────
    inconsistency_warnings = detect_round_inconsistency(df_paired)
    inconsistency_warning_msgs = [msg for _, msg in inconsistency_warnings]
    for msg in inconsistency_warning_msgs:
        notes.append(f"[回数矛盾] {msg}")
    inconsistent_names = {name for name, _ in inconsistency_warnings}

    # ── ペアが0人なら早期終了 ──────────────────────────────────────────────────
    if len(df_paired) == 0:
        msg = (
            "分析対象となるペア（条件AとBの両方に回答した人）が0人です。\n"
            "条件A・条件Bの両方に回答したデータを確認してください。"
        )
        (outdir_path / "report.md").write_text(f"# エラー\n\n{msg}\n", encoding="utf-8")
        raise ValueError(msg)

    # ── エンタメ体験得点 ──────────────────────────────────────
    df_paired["entertainment_score"] = compute_entertainment_score(df_paired)

    # ── wide 形式（1人1行）───────────────────────────────────
    all_metric_cols = config.SCALE_ITEMS + ["entertainment_score"]
    pivot_rows = []
    for name in df_paired["norm_name"].unique():
        person = df_paired[df_paired["norm_name"] == name]
        row: Dict[str, Any] = {"norm_name": name}
        grp = person["group"].iloc[0]
        row["group"] = grp
        for cond_label, cond_val in [("A", config.CONDITION_A), ("B", config.CONDITION_B)]:
            cond_rows = person[person["condition"] == cond_val]
            for col in all_metric_cols:
                if len(cond_rows) > 0 and col in cond_rows.columns:
                    row[f"{col}_{cond_label}"] = cond_rows[col].iloc[0]
                else:
                    row[f"{col}_{cond_label}"] = np.nan
            for col in ["round", "discomfort", "discomfort_interest"]:
                if len(cond_rows) > 0 and col in cond_rows.columns:
                    row[f"{col}_{cond_label}"] = cond_rows[col].iloc[0]
                else:
                    row[f"{col}_{cond_label}"] = None
        pivot_rows.append(row)

    wide_df = pd.DataFrame(pivot_rows)
    wide_df.to_csv(outdir_path / "wide.csv", index=False, encoding="utf-8-sig")

    # ── tidy 形式（name 列を除いて出力し氏名を残さない） ────────
    df_paired.drop(columns=["name"], errors="ignore").to_csv(
        outdir_path / "tidy.csv", index=False, encoding="utf-8-sig"
    )

    # ── Cronbach's α と主指標選択 ────────────────────────────
    def alpha_for_cond(cond):
        sub = df_paired[df_paired["condition"] == cond][config.ENTERTAINMENT_ITEMS].dropna()
        return cronbach_alpha(sub)

    alpha_a = alpha_for_cond(config.CONDITION_A)
    alpha_b = alpha_for_cond(config.CONDITION_B)
    primary_metric, alpha_note = select_primary_metric(alpha_a, alpha_b)
    if alpha_note:
        notes.append(f"[主指標切り替え] {alpha_note}")

    # ── ① 主指標検定 ─────────────────────────────────────────
    valid_pairs = wide_df.dropna(subset=[f"{primary_metric}_A", f"{primary_metric}_B"])
    a_vals = valid_pairs[f"{primary_metric}_A"].values
    b_vals = valid_pairs[f"{primary_metric}_B"].values
    main_result = wilcoxon_signed_rank(a_vals, b_vals)
    main_judgment = judgment_text(main_result["mean_diff"], main_result["p"])

    # ── ② 副指標検定 ─────────────────────────────────────────
    secondary_results = {}
    for item in config.SECONDARY_ITEMS:
        vp = wide_df.dropna(subset=[f"{item}_A", f"{item}_B"])
        av = vp[f"{item}_A"].values
        bv = vp[f"{item}_B"].values
        secondary_results[item] = wilcoxon_signed_rank(av, bv)
    secondary_p_vals = [secondary_results[it]["p"] for it in config.SECONDARY_ITEMS]
    secondary_holm = holm_correction(secondary_p_vals)

    # ── ③ 条件確認 ────────────────────────────────────────────
    condition_check_results = {}
    for item in config.CONDITION_CHECK_ITEMS:
        vp = wide_df.dropna(subset=[f"{item}_A", f"{item}_B"])
        av = vp[f"{item}_A"].values
        bv = vp[f"{item}_B"].values
        res = wilcoxon_signed_rank(av, bv)
        condition_check_results[item] = res
        if abs(res.get("dz", np.nan)) >= config.DZ_WARNING_THRESHOLD:
            notes.append(
                f"[条件確認] '{item}' の |dz| = {_fmt_f(res['dz'])} ≥ {config.DZ_WARNING_THRESHOLD}。"
                "嘘以外の違いも影響した可能性があります。"
            )

    # ── ④ 1回目だけの比較 ────────────────────────────────────
    # グループ1の条件A（1回目） vs グループ2の条件B（1回目）
    # mann_whitney_u(x, y) は x > y で delta > 0 なので、
    # 第1引数にグループ2の条件B（仕様上「大きいと正」の側）を渡す
    grp1_first = wide_df[wide_df["group"] == 1][f"{primary_metric}_A"].dropna().values
    grp2_first = wide_df[wide_df["group"] == 2][f"{primary_metric}_B"].dropna().values
    first_result: Dict[str, Any] = {}
    if len(grp1_first) > 0 and len(grp2_first) > 0:
        first_result = mann_whitney_u(grp2_first, grp1_first)

    # ── ⑤ 順番の影響 ─────────────────────────────────────────
    order_df = df_paired[~df_paired["norm_name"].isin(inconsistent_names)]
    round_wide_rows = []
    for name in order_df["norm_name"].unique():
        person = order_df[order_df["norm_name"] == name]
        first_rows = person[person["round"] == config.ROUND_FIRST]
        second_rows = person[person["round"] == config.ROUND_SECOND]
        if len(first_rows) == 0 or len(second_rows) == 0:
            continue
        round_wide_rows.append({
            "norm_name": name,
            "group": person["group"].iloc[0],
            f"{primary_metric}_1st": first_rows[primary_metric].iloc[0],
            f"{primary_metric}_2nd": second_rows[primary_metric].iloc[0],
        })
    round_wide = pd.DataFrame(round_wide_rows)
    order_result: Dict[str, Any] = {}
    if len(round_wide) >= 2:
        r1 = round_wide[f"{primary_metric}_1st"].values
        r2 = round_wide[f"{primary_metric}_2nd"].values
        order_result = wilcoxon_signed_rank(r1, r2)

    # グループ別 B−A の差の比較 ＋ グループ別条件A・B平均表
    diff_by_group: Dict[str, Any] = {}
    group_means: Dict[str, Any] = {}
    if "group" in wide_df.columns:
        g1 = wide_df[wide_df["group"] == 1]
        g2 = wide_df[wide_df["group"] == 2]
        g1_diff = (g1[f"{primary_metric}_B"] - g1[f"{primary_metric}_A"]).dropna().values
        g2_diff = (g2[f"{primary_metric}_B"] - g2[f"{primary_metric}_A"]).dropna().values
        if len(g1_diff) > 0 and len(g2_diff) > 0:
            diff_by_group = mann_whitney_u(g1_diff, g2_diff)
        # C: グループ別の条件A・B平均
        for grp_num, grp_df in [(1, g1), (2, g2)]:
            a_vals_g = grp_df[f"{primary_metric}_A"].dropna()
            b_vals_g = grp_df[f"{primary_metric}_B"].dropna()
            group_means[grp_num] = {
                "n": len(grp_df),
                "mean_A": float(a_vals_g.mean()) if len(a_vals_g) > 0 else np.nan,
                "mean_B": float(b_vals_g.mean()) if len(b_vals_g) > 0 else np.nan,
                "sd_A": float(a_vals_g.std(ddof=1)) if len(a_vals_g) > 1 else np.nan,
                "sd_B": float(b_vals_g.std(ddof=1)) if len(b_vals_g) > 1 else np.nan,
            }

    # ── ⑥ 違和感 ─────────────────────────────────────────────
    disc_cross = _compute_discomfort_cross(df_paired)
    disc_cross_first = _compute_discomfort_cross(
        df_paired[df_paired["round"] == config.ROUND_FIRST]
    )

    # A: 「興味を抱いたか」を違和感あり人の中で条件別に集計
    disc_interest: Dict[str, Any] = {}
    for cond in [config.CONDITION_A, config.CONDITION_B]:
        cond_sub = df_paired[
            (df_paired["condition"] == cond) &
            (df_paired["discomfort"].isin(config.DISCOMFORT_PRESENT_CATEGORIES))
        ]["discomfort_interest"].dropna()
        total = len(cond_sub)
        hai = config.DISCOMFORT_INTEREST_CHOICES[0]   # "はい"
        iie = config.DISCOMFORT_INTEREST_CHOICES[1]   # "いいえ"
        disc_interest[cond] = {
            "total": total,
            "yes": int((cond_sub == hai).sum()),
            "no": int((cond_sub == iie).sum()),
            "yes_pct": float((cond_sub == hai).sum() / total) if total > 0 else 0.0,
        }

    # B: 違和感あり vs なしで主指標の差を比較
    disc_diff_result: Dict[str, Any] = {}
    b_data = wide_df.dropna(subset=[f"{primary_metric}_A", f"{primary_metric}_B"])
    b_data = b_data.copy()
    b_data["diff"] = b_data[f"{primary_metric}_B"] - b_data[f"{primary_metric}_A"]
    disc_b = df_paired[df_paired["condition"] == config.CONDITION_B][
        ["norm_name", "discomfort"]
    ]
    merged = b_data.merge(disc_b, on="norm_name", how="left")
    no_disc = merged[merged["discomfort"] == config.DISCOMFORT_CATEGORIES[0]]["diff"].dropna().values
    some_disc = merged[merged["discomfort"].isin(config.DISCOMFORT_PRESENT_CATEGORIES)]["diff"].dropna().values
    if len(no_disc) >= 5 and len(some_disc) >= 5:
        disc_diff_result = mann_whitney_u(no_disc, some_disc)
    else:
        notes.append(
            "[違和感] 違和感の有無グループのどちらかが5人未満のため、検定は行わず記述統計のみ。"
        )

    # C: 違和感スコア（0/1/2）と B−A 差のスピアマン相関
    disc_score_map = {cat: i for i, cat in enumerate(config.DISCOMFORT_CATEGORIES)}
    merged_valid = merged.dropna(subset=["diff", "discomfort"])
    disc_scores_sp = merged_valid["discomfort"].map(disc_score_map).astype(float).values
    ba_diffs_sp = merged_valid["diff"].values
    mask_sp = ~(np.isnan(disc_scores_sp) | np.isnan(ba_diffs_sp))
    spearman_result: Dict[str, Any] = {}
    if mask_sp.sum() >= 3:
        spearman_result = spearman_correlation(disc_scores_sp[mask_sp], ba_diffs_sp[mask_sp])
    else:
        notes.append("[違和感] スピアマン相関の計算に十分なデータがありません（3人未満）。")

    # ── ⑦ 記述統計と天井効果 ─────────────────────────────────
    desc_stats = _compute_desc_stats(df_paired)
    for item, row in desc_stats.items():
        if row.get("ceiling_prop_A", 0) >= config.CEILING_EFFECT_THRESHOLD or \
           row.get("ceiling_prop_B", 0) >= config.CEILING_EFFECT_THRESHOLD:
            notes.append(
                f"[天井効果] '{item}': 条件A={row['ceiling_prop_A']:.1%}、"
                f"条件B={row['ceiling_prop_B']:.1%} で9〜10点の割合が高い。"
            )

    # ── ⑧ 自由記述 ────────────────────────────────────────────
    _write_free_text(df_paired, outdir_path)
    _write_coding_sheet(df_paired, outdir_path)
    _write_lie_list(outdir_path)

    # coding_done.csv があれば集計
    coding_done_path = config.ANALYSIS_CODING_DONE_CSV
    lie_detection_result: Dict[str, Any] = {}
    if os.path.exists(coding_done_path):
        lie_detection_result = _summarize_lie_detection(coding_done_path)

    # ── ⑨ 図 ─────────────────────────────────────────────────
    from src.analysis.figures import plot_main_metric, plot_item_means, plot_discomfort
    plot_main_metric(wide_df, primary_metric, figs_dir)
    plot_item_means(df_paired, figs_dir)
    plot_discomfort(df_paired, figs_dir)

    # ── ⑩ レポート生成 ───────────────────────────────────────
    results = {
        "n_raw": len(df_raw),
        "n_dedup": len(df_dedup),
        "n_paired": len(wide_df),
        "excluded": excluded,
        "inconsistency_warnings": inconsistency_warnings,
        "dup_warnings": dup_warnings,
        "group_counts": wide_df["group"].value_counts().to_dict() if "group" in wide_df else {},
        "alpha_a": alpha_a,
        "alpha_b": alpha_b,
        "primary_metric": primary_metric,
        "alpha_note": alpha_note,
        "main_result": main_result,
        "main_judgment": main_judgment,
        "secondary_results": secondary_results,
        "secondary_holm": secondary_holm,
        "condition_check_results": condition_check_results,
        "first_result": first_result,
        "order_result": order_result,
        "diff_by_group": diff_by_group,
        "group_means": group_means,
        "disc_cross": disc_cross,
        "disc_cross_first": disc_cross_first,
        "disc_interest": disc_interest,
        "disc_diff_result": disc_diff_result,
        "spearman_result": spearman_result,
        "disc_no_mean": float(np.mean(no_disc)) if len(no_disc) > 0 else np.nan,
        "disc_some_mean": float(np.mean(some_disc)) if len(some_disc) > 0 else np.nan,
        "no_disc_n": len(no_disc),
        "some_disc_n": len(some_disc),
        "desc_stats": desc_stats,
        "notes": notes,
    }

    report_text = _build_report(results)
    (outdir_path / "report.md").write_text(report_text, encoding="utf-8")

    return results, notes


def _compute_discomfort_cross(sub: pd.DataFrame) -> Dict:
    """違和感のクロス表を計算する。選択肢は config.DISCOMFORT_CATEGORIES を参照。"""
    result = {}
    for cond in [config.CONDITION_A, config.CONDITION_B]:
        cond_sub = sub[sub["condition"] == cond]["discomfort"].dropna()
        total = len(cond_sub)
        result[cond] = {
            cat: {"n": int((cond_sub == cat).sum()),
                  "pct": float((cond_sub == cat).sum() / total) if total > 0 else 0.0}
            for cat in config.DISCOMFORT_CATEGORIES
        }
        result[cond]["total"] = total
    return result


def _compute_desc_stats(df: pd.DataFrame) -> Dict:
    stats = {}
    for item in config.SCALE_ITEMS:
        row: Dict[str, Any] = {}
        for cond_label, cond in [("A", config.CONDITION_A), ("B", config.CONDITION_B)]:
            sub = df[df["condition"] == cond][item].dropna()
            row[f"n_{cond_label}"] = len(sub)
            row[f"mean_{cond_label}"] = float(sub.mean()) if len(sub) > 0 else np.nan
            row[f"sd_{cond_label}"] = float(sub.std(ddof=1)) if len(sub) > 1 else np.nan
            row[f"median_{cond_label}"] = float(sub.median()) if len(sub) > 0 else np.nan
            row[f"q1_{cond_label}"] = float(sub.quantile(0.25)) if len(sub) > 0 else np.nan
            row[f"q3_{cond_label}"] = float(sub.quantile(0.75)) if len(sub) > 0 else np.nan
            ceiling = (sub >= 9).sum() / len(sub) if len(sub) > 0 else 0.0
            row[f"ceiling_prop_{cond_label}"] = float(ceiling)
        stats[item] = row
    return stats


def _write_free_text(df: pd.DataFrame, outdir: Path) -> None:
    free_cols = [
        "norm_name", "condition", "round", "group",
        "discomfort_where", "discomfort_why",
        "discomfort_interest", "no_interest_reason", "interest_reason",
        "impression", "comment",
    ]
    existing = [c for c in free_cols if c in df.columns]
    df[existing].to_csv(outdir / "free_text.csv", index=False, encoding="utf-8-sig")


def _write_coding_sheet(df: pd.DataFrame, outdir: Path) -> None:
    b_disc = df[
        (df["condition"] == config.CONDITION_B) &
        (df["discomfort"].isin(config.DISCOMFORT_PRESENT_CATEGORIES))
    ].copy()
    rows = []
    for _, row in b_disc.iterrows():
        rows.append({
            "氏名": row.get("norm_name", ""),
            "条件": row.get("condition", ""),
            "回数": row.get("round", ""),
            "どこで": row.get("discomfort_where", ""),
            "なぜ": row.get("discomfort_why", ""),
            "該当する嘘ID": "",
            "本当の部分への違和感か": "",
            "メモ": "",
        })
    pd.DataFrame(rows).to_csv(outdir / "coding_sheet.csv", index=False, encoding="utf-8-sig")


def _write_lie_list(outdir: Path) -> None:
    rows = [
        {"ID": lie["id"], "場所": lie["location"], "内容": lie["content"]}
        for lie in config.LIE_LIST
    ]
    pd.DataFrame(rows).to_csv(outdir / "lie_list.csv", index=False, encoding="utf-8-sig")


_ID_SPLIT_RE = re.compile(r"[,、，/・\s]+")


def _parse_lie_ids(raw: str) -> List[str]:
    """嘘IDセル（"H1,K2" や "Ｈ１" 等）を個別IDのリストに分解して返す。
    全角英数字は半角に統一してから分割し、完全一致用の正規化済みIDを返す。
    """
    import unicodedata as ud
    norm = ud.normalize("NFKC", str(raw)).strip()
    return [s.strip() for s in _ID_SPLIT_RE.split(norm) if s.strip()]


def _summarize_lie_detection(coding_done_path: str) -> Dict:
    try:
        df = pd.read_csv(coding_done_path, encoding="utf-8-sig")
    except Exception:
        return {}
    result = {}
    if "該当する嘘ID" not in df.columns:
        return {}

    valid_ids = {lie["id"] for lie in config.LIE_LIST}
    interest_col = "discomfort_interest" if "discomfort_interest" in df.columns else None

    # 各行のIDセルをリストに展開したマップを作っておく
    row_ids: List[List[str]] = df["該当する嘘ID"].apply(
        lambda x: _parse_lie_ids(str(x)) if pd.notna(x) and str(x).strip() else []
    ).tolist()

    # 存在しない ID の警告（呼び出し元に返す手段がないため標準エラーに出す）
    all_ids_in_data = {lid for ids in row_ids for lid in ids}
    unknown = all_ids_in_data - valid_ids - {""}
    if unknown:
        import sys
        print(
            f"[警告] coding_done.csv に存在しない嘘ID が含まれています: {sorted(unknown)}",
            file=sys.stderr,
        )

    for lie in config.LIE_LIST:
        lid = lie["id"]
        matched_rows = [i for i, ids in enumerate(row_ids) if lid in ids]
        n_noticed = len(matched_rows)
        n_interested = 0
        if interest_col and n_noticed > 0:
            n_interested = int(
                (df.iloc[matched_rows][interest_col] == "はい").sum()
            )
        result[lid] = {"n_noticed": n_noticed, "n_interested": n_interested}
    return result


def _build_report(r: Dict) -> str:
    pm = r["primary_metric"]
    mr = r["main_result"]
    lines = [
        "# 事後アンケート分析レポート",
        "",
        "---",
        "",
        "## 1. データの概要",
        "",
        f"- 生データ行数: {r['n_raw']}",
        f"- 重複除去後: {r['n_dedup']}",
        f"- 分析に使用した人数（条件A・B 両方回答）: {r['n_paired']}",
        f"- グループ1（A→B）: {r['group_counts'].get(1, 0)} 人",
        f"- グループ2（B→A）: {r['group_counts'].get(2, 0)} 人",
        "",
    ]

    if r["excluded"]:
        lines.append("### 除外した人")
        lines.append("")
        for e in r["excluded"]:
            lines.append(f"- {e['name']}: {e['reason']}")
        lines.append("")

    if r["dup_warnings"]:
        lines.append("### 重複・警告")
        lines.append("")
        for w in r["dup_warnings"]:
            lines.append(f"- {w}")
        lines.append("")

    if r["inconsistency_warnings"]:
        lines.append("### 回数の矛盾")
        lines.append("")
        for w in r["inconsistency_warnings"]:
            lines.append(f"- {w}")
        lines.append("")

    lines += [
        "---",
        "",
        "## 2. 主指標の判定",
        "",
        f"- Cronbach's α（条件A）: {_fmt_f(r['alpha_a'])}",
        f"- Cronbach's α（条件B）: {_fmt_f(r['alpha_b'])}",
        f"- 使用した主指標: **{pm}**",
    ]
    if r["alpha_note"]:
        lines.append(f"- 注意: {r['alpha_note']}")
    lines += [
        "",
        f"### ウィルコクソンの符号順位検定（{pm}）",
        "",
        f"- 使用人数: {mr['n_used']}（同点除外: {mr['n_tied']} 人）",
        f"- 統計量 W = {_fmt_f(mr['W'])}",
        f"- {_fmt_p(mr['p'])}",
        f"- 効果量 r = {_fmt_f(mr.get('r', np.nan))}、Cohen's dz = {_fmt_f(mr.get('dz', np.nan))}",
        f"- B−A の平均 = {_fmt_f(mr['mean_diff'])}、中央値 = {_fmt_f(mr['median_diff'])}、SD = {_fmt_f(mr['sd_diff'])}",
        f"- 平均の95%CI: {_fmt_ci(mr['ci_mean'])}",
        f"- 中央値のブートストラップ95%CI: {_fmt_ci(mr['ci_median'])}",
        "",
        f"**{r['main_judgment']}**",
        "",
        "---",
        "",
        "## 3. 副指標",
        "",
        "※ 副指標は「傾向」として扱う。Holm 法による補正 p 値も参考として示す。",
        "",
        "| 項目 | n | W | p | r | dz | Holm p |",
        "|------|---|---|---|---|-----|--------|",
    ]
    for i, item in enumerate(config.SECONDARY_ITEMS):
        sr = r["secondary_results"][item]
        holm_p = r["secondary_holm"][i]
        lines.append(
            f"| {item} | {sr['n_used']} | {_fmt_f(sr['W'])} | {_fmt_p(sr['p'])} "
            f"| {_fmt_f(sr.get('r', np.nan))} | {_fmt_f(sr.get('dz', np.nan))} "
            f"| {_fmt_p(holm_p)} |"
        )
    lines += [
        "",
        "---",
        "",
        "## 4. 条件の確認（嘘以外の差）",
        "",
        "※ 目的は「差が0に近いこと」の確認。検定の p 値は参考として示す。",
        "",
        "| 項目 | mean A | mean B | dz | r | p |",
        "|------|--------|--------|-----|---|---|",
    ]
    desc = r["desc_stats"]
    for item in config.CONDITION_CHECK_ITEMS:
        cr = r["condition_check_results"][item]
        lines.append(
            f"| {item} "
            f"| {_fmt_f(desc[item]['mean_A'], 2)} "
            f"| {_fmt_f(desc[item]['mean_B'], 2)} "
            f"| {_fmt_f(cr.get('dz', np.nan))} "
            f"| {_fmt_f(cr.get('r', np.nan))} "
            f"| {_fmt_p(cr['p'])} |"
        )
    lines += [
        "",
        "---",
        "",
        "## 5. 1回目だけの比較（補足）",
        "",
        "※ 人数が少ないため「傾向」として扱う。",
        "※ Cliff's δ は正の値が条件B（グループ2の1回目）のほうが高いことを示す。",
        "",
    ]
    fr = r["first_result"]
    if fr:
        lines += [
            f"- マン・ホイットニーの U = {_fmt_f(fr.get('U', np.nan))}",
            f"- {_fmt_p(fr['p'])}",
            f"- r = {_fmt_f(fr.get('r', np.nan))}、Cliff's δ = {_fmt_f(fr.get('delta', np.nan))}",
        ]
    else:
        lines.append("- データが不十分なため計算できませんでした。")
    lines += [
        "",
        "---",
        "",
        "## 6. 順番の影響",
        "",
    ]
    orr = r["order_result"]
    if orr:
        lines += [
            f"- ウィルコクソン（1回目 vs 2回目）: {_fmt_p(orr['p'])}、r = {_fmt_f(orr.get('r', np.nan))}",
        ]
    else:
        lines.append("- データが不十分なため計算できませんでした。")
    dbg = r["diff_by_group"]
    if dbg:
        lines += [
            f"- グループ1 vs グループ2の B−A 差のマン・ホイットニー: {_fmt_p(dbg['p'])}",
        ]
        if dbg.get("p", 1.0) < config.ALPHA_LEVEL:
            lines.append("  ⚠ 順番によって嘘の効果が変わった可能性があります。")
    # C: グループ別の条件A・B平均表
    gm = r.get("group_means", {})
    if gm:
        lines += [
            "",
            f"### グループ別 {pm} の平均",
            "",
            f"| グループ | n | mean {config.CONDITION_A} | SD A | mean {config.CONDITION_B} | SD B |",
            "|---------|---|---------|------|---------|------|",
        ]
        for grp_num, label in [(1, "グループ1（A→B）"), (2, "グループ2（B→A）")]:
            g = gm.get(grp_num, {})
            lines.append(
                f"| {label} | {g.get('n', 0)} "
                f"| {_fmt_f(g.get('mean_A', np.nan), 2)} | {_fmt_f(g.get('sd_A', np.nan), 2)} "
                f"| {_fmt_f(g.get('mean_B', np.nan), 2)} | {_fmt_f(g.get('sd_B', np.nan), 2)} |"
            )
    lines += [
        "",
        "---",
        "",
        "## 7. 違和感（嘘の受け取られ方）",
        "",
        "### 全体",
        "",
        "| 条件 | なかった | 少しあった | あった | 合計 |",
        "|------|----------|------------|--------|------|",
    ]
    for cond in [config.CONDITION_A, config.CONDITION_B]:
        dc = r["disc_cross"].get(cond, {})
        total = dc.get("total", 0)
        lines.append(
            f"| {cond} "
            f"| {dc.get('なかった', {}).get('n', 0)} ({dc.get('なかった', {}).get('pct', 0):.0%}) "
            f"| {dc.get('少しあった', {}).get('n', 0)} ({dc.get('少しあった', {}).get('pct', 0):.0%}) "
            f"| {dc.get('あった', {}).get('n', 0)} ({dc.get('あった', {}).get('pct', 0):.0%}) "
            f"| {total} |"
        )
    lines += [
        "",
        "### 1回目のみ",
        "",
        "| 条件 | なかった | 少しあった | あった | 合計 |",
        "|------|----------|------------|--------|------|",
    ]
    for cond in [config.CONDITION_A, config.CONDITION_B]:
        dc = r["disc_cross_first"].get(cond, {})
        total = dc.get("total", 0)
        lines.append(
            f"| {cond} "
            f"| {dc.get('なかった', {}).get('n', 0)} ({dc.get('なかった', {}).get('pct', 0):.0%}) "
            f"| {dc.get('少しあった', {}).get('n', 0)} ({dc.get('少しあった', {}).get('pct', 0):.0%}) "
            f"| {dc.get('あった', {}).get('n', 0)} ({dc.get('あった', {}).get('pct', 0):.0%}) "
            f"| {total} |"
        )
    # A: 「興味を抱いたか」の条件別集計（違和感あり人の中で）
    disc_int = r.get("disc_interest", {})
    if disc_int:
        lines += [
            "",
            "### 違和感があった人の中での「興味を抱いたか」",
            "",
            "| 条件 | 対象人数 | はい | いいえ | はいの割合 |",
            "|------|----------|------|--------|------------|",
        ]
        for cond in [config.CONDITION_A, config.CONDITION_B]:
            di = disc_int.get(cond, {})
            lines.append(
                f"| {cond} | {di.get('total', 0)} "
                f"| {di.get('yes', 0)} | {di.get('no', 0)} "
                f"| {di.get('yes_pct', 0.0):.0%} |"
            )
    # B: 違和感有無 × 主指標の差
    ddr = r.get("disc_diff_result", {})
    lines += ["", "### 違和感の有無と主指標（B−A）の差"]
    if ddr:
        lines += [
            "",
            f"- 違和感なし: B−A 平均 = {_fmt_f(r.get('disc_no_mean', np.nan))}（n = {r.get('no_disc_n', 0)}）",
            f"- 違和感あり: B−A 平均 = {_fmt_f(r.get('disc_some_mean', np.nan))}（n = {r.get('some_disc_n', 0)}）",
            f"- マン・ホイットニー U = {_fmt_f(ddr.get('U', np.nan))}、{_fmt_p(ddr['p'])}、r = {_fmt_f(ddr.get('r', np.nan))}",
        ]
    else:
        lines.append("")
        lines.append(
            f"- 違和感なし: B−A 平均 = {_fmt_f(r.get('disc_no_mean', np.nan))}"
        )
        lines.append(
            f"- 違和感あり: B−A 平均 = {_fmt_f(r.get('disc_some_mean', np.nan))}"
        )
        lines.append("- 人数が5人未満のため検定は実施しない（記述統計のみ）。")
    # C: スピアマン相関（違和感スコア 0/1/2 vs B−A 差）
    sp = r.get("spearman_result", {})
    lines += ["", "### 違和感スコア（0〜2）と主指標 B−A 差のスピアマン相関"]
    if sp and not np.isnan(sp.get("rho", np.nan)):
        lines += [
            "",
            f"- ρ = {_fmt_f(sp.get('rho', np.nan))}",
            f"- {_fmt_p(sp.get('p', np.nan))}",
            f"- n = {sp.get('n', 0)}",
            "",
            "※ ρ > 0 なら「違和感が強いほど B の得点が A より高い」傾向を示す。",
        ]
    else:
        lines += ["", "- データが不十分なため計算できませんでした。"]
    lines += [
        "",
        "---",
        "",
        "## 8. 記述統計と天井効果",
        "",
        "| 項目 | n A | mean A | SD A | median A | n B | mean B | SD B | median B | 天井A | 天井B |",
        "|------|-----|--------|------|----------|-----|--------|------|----------|-------|-------|",
    ]
    for item in config.SCALE_ITEMS:
        d = r["desc_stats"][item]
        ceiling_warn_a = "⚠" if d.get("ceiling_prop_A", 0) >= config.CEILING_EFFECT_THRESHOLD else ""
        ceiling_warn_b = "⚠" if d.get("ceiling_prop_B", 0) >= config.CEILING_EFFECT_THRESHOLD else ""
        lines.append(
            f"| {item} "
            f"| {d['n_A']} | {_fmt_f(d['mean_A'], 2)} | {_fmt_f(d['sd_A'], 2)} | {_fmt_f(d['median_A'], 1)} "
            f"| {d['n_B']} | {_fmt_f(d['mean_B'], 2)} | {_fmt_f(d['sd_B'], 2)} | {_fmt_f(d['median_B'], 1)} "
            f"| {d['ceiling_prop_A']:.0%}{ceiling_warn_a} | {d['ceiling_prop_B']:.0%}{ceiling_warn_b} |"
        )
    lines += [
        "",
        "---",
        "",
        "## 9. 注意書きの一覧",
        "",
    ]
    if r["notes"]:
        for note in r["notes"]:
            lines.append(f"- {note}")
    else:
        lines.append("- 特記事項なし")
    lines.append("")

    return "\n".join(lines)
