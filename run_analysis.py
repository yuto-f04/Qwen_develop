"""run_analysis.py -- アンケート分析エントリポイント

使い方:
    python run_analysis.py
    python run_analysis.py --input data/responses.csv --outdir output/analysis
"""
import argparse
import io
import sys

# Windows cp932 環境での日本語出力対策
if sys.stdout.encoding and sys.stdout.encoding.lower() in ("cp932", "shift_jis", "mbcs"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from src import config
from src.analysis.report import run_analysis


def main():
    parser = argparse.ArgumentParser(description="事後アンケート分析")
    parser.add_argument(
        "--input",
        default=config.ANALYSIS_INPUT_CSV,
        help=f"入力CSVのパス（デフォルト: {config.ANALYSIS_INPUT_CSV}）",
    )
    parser.add_argument(
        "--outdir",
        default=config.ANALYSIS_OUTPUT_DIR,
        help=f"出力ディレクトリ（デフォルト: {config.ANALYSIS_OUTPUT_DIR}）",
    )
    parser.add_argument(
        "--aliases",
        default=config.ANALYSIS_NAME_ALIASES_CSV,
        help="氏名エイリアスCSVのパス（任意）",
    )
    args = parser.parse_args()

    print(f"入力: {args.input}")
    print(f"出力先: {args.outdir}")
    print()

    try:
        results, notes = run_analysis(
            input_csv=args.input,
            outdir=args.outdir,
            aliases_path=args.aliases,
        )
    except ValueError as e:
        print(f"\n[エラー] {e}", file=sys.stderr)
        sys.exit(1)

    # ── 結果サマリを端末に表示 ─────────────────────────────────
    pm = results["primary_metric"]
    mr = results["main_result"]
    p_str = f"p < .001" if mr["p"] < 0.001 else f"p = {mr['p']:.3f}"
    r_str = f"{mr.get('r', float('nan')):.3f}"
    dz_str = f"{mr.get('dz', float('nan')):.3f}"

    print("=" * 60)
    print("【分析結果サマリ】")
    print(f"  主指標       : {pm}")
    print(f"  使用人数     : {mr['n_used']} 人（同点除外: {mr['n_tied']} 人）")
    print(f"  検定結果     : W = {mr['W']:.3f}, {p_str}, r = {r_str}, dz = {dz_str}")
    print(f"  判定         : {results['main_judgment']}")
    print("=" * 60)
    print(f"\nレポート: {args.outdir}/report.md")

    if notes:
        print(f"\n注意書き ({len(notes)} 件) - report.md の「9. 注意書きの一覧」を参照")


if __name__ == "__main__":
    main()
