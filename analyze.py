"""analyze.py — 事後アンケート分析エントリポイント

使い方:
  python analyze.py 回答.csv                        # 本番データを分析
  python analyze.py --dummy                         # ダミーデータを生成して分析
  python analyze.py --generate-dummy data/dummy.csv # ダミーCSVを保存して終了
  python analyze.py 回答.csv --outdir results/      # 出力先を変更
  python analyze.py 回答.csv --aliases data/name_aliases.csv  # 氏名エイリアスを使用
"""
import argparse
import sys
import tempfile
from pathlib import Path

import numpy as np


def _fmt_p(p: float) -> str:
    if np.isnan(p):
        return "NaN"
    return "p < .001" if p < 0.001 else f"p = {p:.3f}"


def _print_section(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


def _run(csv_path: str, outdir: str, aliases_path: str = "") -> None:
    from src.analysis.report import run_analysis

    print(f"\n[分析開始]  {csv_path}")
    print(f"[出力先]    {outdir}")

    try:
        results, notes = run_analysis(csv_path, outdir, aliases_path=aliases_path)
    except ValueError as e:
        print(f"\n[エラー] {e}", file=sys.stderr)
        sys.exit(1)

    _print_section("データの概要")
    print(f"  生データ: {results['n_raw']} 行")
    print(f"  重複除去後: {results['n_dedup']} 行")
    print(f"  分析対象ペア: {results['n_paired']} 人")
    print(f"  グループ1（A→B）: {results['group_counts'].get(1, 0)} 人")
    print(f"  グループ2（B→A）: {results['group_counts'].get(2, 0)} 人")

    if results["excluded"]:
        print(f"\n  [除外] {len(results['excluded'])} 人")
        for e in results["excluded"]:
            print(f"    {e['name']}: {e['reason']}")

    _print_section("主指標")
    pm = results["primary_metric"]
    print(f"  Cronbach's α: 条件A = {results['alpha_a']:.3f}  /  条件B = {results['alpha_b']:.3f}")
    print(f"  使用した主指標: {pm}")
    if results.get("alpha_note"):
        print(f"  ⚠ {results['alpha_note']}")

    mr = results["main_result"]
    print(f"\n  ウィルコクソン: W = {mr['W']:.1f}  /  {_fmt_p(mr['p'])}")
    print(f"  効果量: r = {mr.get('r', float('nan')):.3f}  /  dz = {mr.get('dz', float('nan')):.3f}")
    print(f"  B−A 差: 平均 = {mr['mean_diff']:.2f}  /  中央値 = {mr['median_diff']:.2f}")
    print(f"  同点除外: {mr['n_tied']} 人  /  検定使用: {mr['n_used']} 人")
    print(f"\n  → {results['main_judgment']}")

    sp = results.get("spearman_result", {})
    if sp and not np.isnan(sp.get("rho", float("nan"))):
        _print_section("違和感スコア vs B−A 差（スピアマン相関）")
        print(f"  ρ = {sp['rho']:.3f}  /  {_fmt_p(sp['p'])}  /  n = {sp['n']}")

    if notes:
        _print_section("注意事項")
        for note in notes:
            print(f"  ⚠ {note}")

    _print_section("出力ファイル")
    for f in sorted(Path(outdir).rglob("*")):
        if f.is_file():
            print(f"  {f.relative_to(outdir)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="事後アンケート分析",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("csv", nargs="?", help="入力CSVファイルのパス")
    parser.add_argument(
        "--outdir", default="output/analysis",
        help="出力ディレクトリ（デフォルト: output/analysis）",
    )
    parser.add_argument("--aliases", default="", help="氏名エイリアスCSVのパス（任意）")
    parser.add_argument(
        "--dummy", action="store_true",
        help="ダミーデータ（20人分）を生成して分析する",
    )
    parser.add_argument(
        "--generate-dummy", metavar="PATH",
        help="ダミーCSVを PATH に保存して終了",
    )
    parser.add_argument("--seed", type=int, default=42, help="ダミーデータ生成シード（デフォルト: 42）")
    args = parser.parse_args()

    if args.generate_dummy:
        from src.analysis.dummy import generate_dummy_csv
        path = Path(args.generate_dummy)
        path.parent.mkdir(parents=True, exist_ok=True)
        df = generate_dummy_csv(seed=args.seed)
        df.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"ダミーデータを保存しました: {path}  ({len(df)} 行)")
        return

    if args.dummy:
        from src.analysis.dummy import generate_dummy_csv
        with tempfile.NamedTemporaryFile(
            suffix=".csv", delete=False, mode="w", encoding="utf-8-sig", newline=""
        ) as f:
            tmp_path = f.name
        df = generate_dummy_csv(seed=args.seed)
        df.to_csv(tmp_path, index=False, encoding="utf-8-sig")
        print(f"ダミーデータを生成しました（{len(df)} 行）: {tmp_path}")
        _run(tmp_path, args.outdir, aliases_path=args.aliases)
        return

    if not args.csv:
        parser.print_help()
        sys.exit(1)

    _run(args.csv, args.outdir, aliases_path=args.aliases)


if __name__ == "__main__":
    main()
