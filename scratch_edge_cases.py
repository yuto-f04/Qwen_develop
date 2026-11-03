"""意地悪なデータで run_analysis を実行し、結果を記録するスクリプト
点検4: 27パターンのうち run_analysis に渡せるもの全てをテスト
"""
import io
import os
import sys
import subprocess
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

PYTHON = sys.executable
BASE_DIR = Path(__file__).parent

HEADER_UTF8 = (
    "タイムスタンプ,"
    "1. 体験者の氏名,"
    "2. ツアーの条件,"
    "3. 何回目の参加ですか？,"
    "4. ツアー内容に興味を持ちましたか？,"
    "5. ツアーの長さは適切でしたか？,"
    "6. ツアー中の説明は分かりやすかったですか？,"
    "7. ガイドの語りに熱意を感じましたか？,"
    "8. このツアーを他人におすすめできますか？,"
    "9. ツアーは期待通りでしたか？,"
    "10. このツアーに満足しましたか？,"
    "11. ツアー内容は難しいと感じましたか？,"
    "12. 体力面で不安は感じましたか？,"
    "13. また参加したいと感じましたか？,"
    "14. ツアーの説明の中に「違和感」「気になったところ」はありましたか？,"
    "14-2. どこで「違和感」を感じたか？,"
    "14-3. なぜ「違和感」を抱いたのか？,"
    "14-4. その違和感に「興味」を抱いたか？,"
    "14-4-2. 興味を抱かなかった理由について簡単に教えてください,"
    "14-4-2. 興味を抱いた理由を簡単に教えてください,"
    "15. ツアーの中で最も印象に残った場面・体験を教えてください,"
    "16. ツアー全体の感想を教えてください  "
)

def base_row(name, cond, rnd, vals="7,7,7,7,7,7,7,7,7,7", disc="なかった"):
    return f"2026/11/01 10:00:00,{name},{cond},{rnd},{vals},{disc},,,,,感想テスト"

def paired_rows(name, cond_a_first=True, vals_a="7,7,7,7,7,7,7,7,7,7", vals_b="8,8,8,8,8,8,8,8,8,8"):
    if cond_a_first:
        r1 = base_row(name, "条件A", "1回目", vals_a)
        r2 = base_row(name, "条件B", "2回目", vals_b)
    else:
        r1 = base_row(name, "条件B", "1回目", vals_b)
        r2 = base_row(name, "条件A", "2回目", vals_a)
    return r1, r2

def make_20_pairs(cond_a_first=True, vals_a="7,7,7,7,7,7,7,7,7,7", vals_b="8,8,8,8,8,8,8,8,8,8", disc_b="なかった"):
    rows = []
    names = [f"テスト{i:02d}" for i in range(1, 21)]
    for i, nm in enumerate(names):
        if cond_a_first:
            r1 = base_row(nm, "条件A", "1回目", vals_a)
            r2 = base_row(nm, "条件B", "2回目", vals_b, disc_b)
        else:
            r1 = base_row(nm, "条件B", "1回目", vals_b, disc_b)
            r2 = base_row(nm, "条件A", "2回目", vals_a)
        rows.extend([r1, r2])
    return rows

def run_analysis(csv_content: bytes, label: str, encoding_write: str = "utf-8-sig",
                 aliases=None, expect_error=False):
    """一時ファイルにCSVを書いて run_analysis.py を実行し、結果を返す"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        csv_path = tmpdir / "responses.csv"
        csv_path.write_bytes(csv_content)
        outdir = tmpdir / "output"
        cmd = [PYTHON, "run_analysis.py", "--input", str(csv_path), "--outdir", str(outdir)]
        if aliases:
            alias_path = tmpdir / "aliases.csv"
            alias_path.write_text(aliases, encoding="utf-8")
            cmd.extend(["--aliases", str(alias_path)])
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", env=env, cwd=str(BASE_DIR))
        ok = result.returncode == 0
        report_text = ""
        if ok:
            rp = outdir / "report.md"
            if rp.exists():
                report_text = rp.read_text(encoding="utf-8")
        status = "OK" if ok else "ERROR"
        if expect_error and not ok:
            status = "EXPECTED_ERROR"
        elif expect_error and ok:
            status = "SHOULD_HAVE_ERRORED"
        return {
            "label": label,
            "status": status,
            "returncode": result.returncode,
            "stdout": result.stdout[:300],
            "stderr": result.stderr[:300],
            "report": report_text[:500],
        }


results = []

# ─── ファイル形式 ─────────────────────────────────────────────────────────────

# #1 BOMなし UTF-8
rows = make_20_pairs()
content = (HEADER_UTF8 + "\n" + "\n".join(rows) + "\n").encode("utf-8")  # no BOM
r = run_analysis(content, "#1 BOMなし UTF-8")
results.append(r)

# #2 BOM付き UTF-8（正常系）
content_bom = (HEADER_UTF8 + "\n" + "\n".join(rows) + "\n").encode("utf-8-sig")
r = run_analysis(content_bom, "#2 BOM付き UTF-8（正常）")
results.append(r)

# #3 CP932（Shift-JIS）
try:
    content_cp932 = (HEADER_UTF8 + "\n" + "\n".join(rows) + "\n").encode("cp932")
    r = run_analysis(content_cp932, "#3 CP932/Shift-JIS", expect_error=True)
except UnicodeEncodeError:
    results.append({"label": "#3 CP932/Shift-JIS", "status": "SKIP(encode_error)", "returncode": -1, "stdout":"", "stderr":"", "report":""})

# #4 CRLF改行
content_crlf = (HEADER_UTF8 + "\r\n" + "\r\n".join(rows) + "\r\n").encode("utf-8-sig")
r = run_analysis(content_crlf, "#4 CRLF改行")
results.append(r)

# #5 ヘッダーだけ（回答0件）
content_hdr = (HEADER_UTF8 + "\n").encode("utf-8-sig")
r = run_analysis(content_hdr, "#5 ヘッダーだけ")
results.append(r)

# #6 1件だけ
content_1 = (HEADER_UTF8 + "\n" + base_row("テスト01", "条件A", "1回目") + "\n").encode("utf-8-sig")
r = run_analysis(content_1, "#6 1件のみ")
results.append(r)

# #7 余分な列
header_extra = HEADER_UTF8 + ",メールアドレス,スコア"
rows_extra = [base_row("テスト01", "条件A", "1回目") + ",test@example.com,100",
              base_row("テスト01", "条件B", "2回目") + ",test@example.com,200"]
content_extra = (header_extra + "\n" + "\n".join(rows_extra) + "\n").encode("utf-8-sig")
r = run_analysis(content_extra, "#7 余分な列")
results.append(r)

# #8 必須列が1つ無い（氏名列を除く）
import pandas as pd
# 氏名列だけ抜いたCSV
df_miss = pd.read_csv(io.StringIO(HEADER_UTF8 + "\n" + "\n".join(rows[:4])), encoding="utf-8-sig")
df_miss = df_miss.drop(columns=["1. 体験者の氏名"], errors="ignore")
buf = io.BytesIO()
df_miss.to_csv(buf, index=False, encoding="utf-8-sig")
r = run_analysis(buf.getvalue(), "#8 必須列なし（氏名）", expect_error=True)
results.append(r)

# #9 タイムスタンプ形式違い1 (slash)
row_ts1 = "2026/11/10 13:05:22,テスト01,条件A,1回目,7,7,7,7,7,7,7,7,7,7,なかった,,,,,感想"
row_ts1b = "2026/11/10 13:06:00,テスト01,条件B,2回目,8,8,8,8,8,8,8,8,8,8,なかった,,,,,感想"
content_ts1 = (HEADER_UTF8 + "\n" + row_ts1 + "\n" + row_ts1b + "\n").encode("utf-8-sig")
r = run_analysis(content_ts1, "#9a タイムスタンプ: 2026/11/10 13:05:22")
results.append(r)

# #10 タイムスタンプ形式違い2: 午後表記
row_ts2 = "2026/11/10 午後 1:05:22,テスト01,条件A,1回目,7,7,7,7,7,7,7,7,7,7,なかった,,,,,感想"
row_ts2b = "2026/11/10 午後 1:06:00,テスト01,条件B,2回目,8,8,8,8,8,8,8,8,8,8,なかった,,,,,感想"
content_ts2 = (HEADER_UTF8 + "\n" + row_ts2 + "\n" + row_ts2b + "\n").encode("utf-8-sig")
r = run_analysis(content_ts2, "#9b タイムスタンプ: 午後表記")
results.append(r)

# ─── 氏名突き合わせ ───────────────────────────────────────────────────────────

# #11 全角スペース・半角スペースの表記ゆれ（同一人物として扱えるか）
r_typo1 = base_row("テスト　01", "条件A", "1回目")  # 全角スペース
r_typo2 = base_row("テスト01", "条件B", "2回目")
content_typo = (HEADER_UTF8 + "\n" + r_typo1 + "\n" + r_typo2 + "\n").encode("utf-8-sig")
r = run_analysis(content_typo, "#11 全角スペース表記ゆれ（同一人物）")
results.append(r)

# #12 name_aliases.csv で直せるか（カタカナ→ひらがな等）
r_kata = base_row("テストイチ", "条件A", "1回目")
r_hira = base_row("てすといち", "条件B", "2回目")
content_alias = (HEADER_UTF8 + "\n" + r_kata + "\n" + r_hira + "\n").encode("utf-8-sig")
aliases_csv = "alias,name\nてすといち,テストイチ\n"
r = run_analysis(content_alias, "#12 aliases.csvで統一", aliases=aliases_csv)
results.append(r)

# #13 重複（同一人物が同条件を2回送信）→ 新しいほうを使い警告
rows_dup = [
    "2026/11/01 09:00:00,テスト01,条件A,1回目,5,5,5,5,5,5,5,5,5,5,なかった,,,,,",
    "2026/11/01 10:00:00,テスト01,条件A,1回目,9,9,9,9,9,9,9,9,9,9,なかった,,,,,",
    "2026/11/01 10:30:00,テスト01,条件B,2回目,8,8,8,8,8,8,8,8,8,8,なかった,,,,,",
]
content_dup = (HEADER_UTF8 + "\n" + "\n".join(rows_dup) + "\n").encode("utf-8-sig")
r = run_analysis(content_dup, "#13 重複回答（古い5点を新しい9点で上書き）")
results.append(r)

# #14 片方しか回答していない人
rows_partial = [
    base_row("テスト01", "条件A", "1回目"),
    base_row("テスト01", "条件B", "2回目"),
    base_row("テスト片方", "条件A", "1回目"),
]
content_partial = (HEADER_UTF8 + "\n" + "\n".join(rows_partial) + "\n").encode("utf-8-sig")
r = run_analysis(content_partial, "#14 片方のみ回答者")
results.append(r)

# #15 両方とも条件A と答えた人（回答ミス）
rows_err = [
    base_row("テスト01", "条件A", "1回目"),
    base_row("テスト01", "条件A", "2回目"),
]
content_err = (HEADER_UTF8 + "\n" + "\n".join(rows_err) + "\n").encode("utf-8-sig")
r = run_analysis(content_err, "#15 両方とも条件A（回答ミス）")
results.append(r)

# #16 両方とも1回目と答えた人
rows_err2 = [
    base_row("テスト01", "条件A", "1回目"),
    base_row("テスト01", "条件B", "1回目"),
]
content_err2 = (HEADER_UTF8 + "\n" + "\n".join(rows_err2) + "\n").encode("utf-8-sig")
r = run_analysis(content_err2, "#16 両方とも1回目（回答ミス）")
results.append(r)

# #17 氏名が空欄
rows_blank = [
    base_row("", "条件A", "1回目"),
    base_row("テスト01", "条件A", "1回目"),
    base_row("テスト01", "条件B", "2回目"),
]
content_blank = (HEADER_UTF8 + "\n" + "\n".join(rows_blank) + "\n").encode("utf-8-sig")
r = run_analysis(content_blank, "#17 氏名が空欄")
results.append(r)

# ─── 得点 ────────────────────────────────────────────────────────────────────

# #18 範囲外（0、11）
rows_range = make_20_pairs()
rows_range.append(base_row("テスト21", "条件A", "1回目", "0,7,7,7,7,7,7,7,7,11"))
rows_range.append(base_row("テスト21", "条件B", "2回目", "7,7,7,7,7,7,7,7,7,7"))
content_range = (HEADER_UTF8 + "\n" + "\n".join(rows_range) + "\n").encode("utf-8-sig")
r = run_analysis(content_range, "#18 範囲外スコア（0と11）")
results.append(r)

# #19 全角数字
rows_full = make_20_pairs()
rows_full[0] = rows_full[0].replace(",7,7,7,7,7,7,7,7,7,7,なかった", ",５,7,7,7,7,7,7,7,7,7,なかった")
content_full = (HEADER_UTF8 + "\n" + "\n".join(rows_full) + "\n").encode("utf-8-sig")
r = run_analysis(content_full, "#19 全角数字（'５'）")
results.append(r)

# #20 全員同じ点（分散0）→ α・dz・検定がゼロ除算で落ちないか
rows_zero_var = make_20_pairs(vals_a="7,7,7,7,7,7,7,7,7,7", vals_b="7,7,7,7,7,7,7,7,7,7")
content_zero_var = (HEADER_UTF8 + "\n" + "\n".join(rows_zero_var) + "\n").encode("utf-8-sig")
r = run_analysis(content_zero_var, "#20 全員同点（分散0）")
results.append(r)

# #21 全員 B>A で有意
rows_b_wins = make_20_pairs(vals_a="3,3,3,3,3,3,3,3,3,3", vals_b="9,9,9,9,9,9,9,9,9,9")
content_b_wins = (HEADER_UTF8 + "\n" + "\n".join(rows_b_wins) + "\n").encode("utf-8-sig")
r = run_analysis(content_b_wins, "#21 全員B>Aで有意")
results.append(r)

# #22 A>B で有意
rows_a_wins = make_20_pairs(vals_a="9,9,9,9,9,9,9,9,9,9", vals_b="3,3,3,3,3,3,3,3,3,3")
content_a_wins = (HEADER_UTF8 + "\n" + "\n".join(rows_a_wins) + "\n").encode("utf-8-sig")
r = run_analysis(content_a_wins, "#22 A>Bで有意（判定文の確認）")
results.append(r)

# #23 全員 9〜10 点（天井効果）
rows_ceil = make_20_pairs(vals_a="9,9,9,9,9,9,9,9,9,9", vals_b="10,10,10,10,10,10,10,10,10,10")
content_ceil = (HEADER_UTF8 + "\n" + "\n".join(rows_ceil) + "\n").encode("utf-8-sig")
r = run_analysis(content_ceil, "#23 全員9〜10点（天井効果）")
results.append(r)

# #24 α < 0.70（一方のみ）→ satisfaction に切り替わるか
# 条件A: 全員同一スコア（α低）、条件B: ばらつきあり（α高）
rows_alpha = []
names = [f"テスト{i:02d}" for i in range(1, 21)]
for i, nm in enumerate(names[:10]):
    rows_alpha.append(base_row(nm, "条件A", "1回目", "5,5,5,5,5,5,5,5,5,5"))
    rows_alpha.append(base_row(nm, "条件B", "2回目", f"{i%8+3},{i%7+4},{i%9+2},{i%8+3},5,5,5,5,5,5"))
for i, nm in enumerate(names[10:]):
    rows_alpha.append(base_row(nm, "条件B", "1回目", f"{i%8+3},{i%7+4},{i%9+2},{i%8+3},5,5,5,5,5,5"))
    rows_alpha.append(base_row(nm, "条件A", "2回目", "5,5,5,5,5,5,5,5,5,5"))
content_alpha = (HEADER_UTF8 + "\n" + "\n".join(rows_alpha) + "\n").encode("utf-8-sig")
r = run_analysis(content_alpha, "#24 α切り替え（条件Aが低α）")
results.append(r)

# #25 違和感ありが5人未満
rows_disc_few = make_20_pairs(disc_b="なかった")  # 全員違和感なし
content_disc = (HEADER_UTF8 + "\n" + "\n".join(rows_disc_few) + "\n").encode("utf-8-sig")
r = run_analysis(content_disc, "#25 違和感ありが0人（5人未満）")
results.append(r)

# #26 人数が少ない（3人）
rows_3 = []
for nm in ["テスト01", "テスト02", "テスト03"]:
    rows_3.append(base_row(nm, "条件A", "1回目", "5,5,5,5,5,5,5,5,5,5"))
    rows_3.append(base_row(nm, "条件B", "2回目", "7,7,7,7,7,7,7,7,7,7"))
content_3 = (HEADER_UTF8 + "\n" + "\n".join(rows_3) + "\n").encode("utf-8-sig")
r = run_analysis(content_3, "#26 3人だけ")
results.append(r)

# #27 グループの人数が偏る（グループ2が0人）
rows_g1_only = []
names_g1 = [f"テスト{i:02d}" for i in range(1, 11)]
for nm in names_g1:
    rows_g1_only.append(base_row(nm, "条件A", "1回目"))
    rows_g1_only.append(base_row(nm, "条件B", "2回目"))
content_g1 = (HEADER_UTF8 + "\n" + "\n".join(rows_g1_only) + "\n").encode("utf-8-sig")
r = run_analysis(content_g1, "#27 グループ2が0人（全員グループ1）")
results.append(r)

# ─── 自由記述 ────────────────────────────────────────────────────────────────

# #28 自由記述にカンマ・改行・ダブルクォート
# CSVエスケープが必要
import csv, io as io2
buf = io2.StringIO()
writer = csv.writer(buf)
header_list = HEADER_UTF8.split(",")
writer.writerow(header_list)
writer.writerow([
    "2026/11/01 10:00:00", "テスト01", "条件A", "1回目",
    7,7,7,7,7,7,7,7,7,7,
    "あった", "KOBO", 'コンマ,改行\nあり"引用符"', "はい", "", "理由テスト 😀",
    "印象,テスト\n改行", "感想テスト"
])
writer.writerow([
    "2026/11/01 11:00:00", "テスト01", "条件B", "2回目",
    8,8,8,8,8,8,8,8,8,8,
    "なかった", "", "", "", "", "", "", "感想"
])
content_csv_escape = buf.getvalue().encode("utf-8-sig")
r = run_analysis(content_csv_escape, "#28 自由記述にカンマ・改行・クォート・絵文字")
results.append(r)

# ─── 実行環境 ─────────────────────────────────────────────────────────────────

# #29 2回続けて実行（上書き）
rows_dup_run = make_20_pairs()
content_normal = (HEADER_UTF8 + "\n" + "\n".join(rows_dup_run) + "\n").encode("utf-8-sig")
with tempfile.TemporaryDirectory() as tmpdir:
    tmpdir_p = Path(tmpdir)
    csv_p = tmpdir_p / "responses.csv"
    csv_p.write_bytes(content_normal)
    outdir_p = tmpdir_p / "output"
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    for run_n in range(2):
        res = subprocess.run([PYTHON, "run_analysis.py", "--input", str(csv_p), "--outdir", str(outdir_p)],
                             capture_output=True, text=True, encoding="utf-8", env=env, cwd=str(BASE_DIR))
    ok = res.returncode == 0
    results.append({"label": "#29 2回続けて実行（上書き）", "status": "OK" if ok else "ERROR",
                    "returncode": res.returncode, "stdout": res.stdout[:200], "stderr": res.stderr[:200], "report": ""})

# ─── 出力 ────────────────────────────────────────────────────────────────────

print("\n" + "="*70)
print("意地悪データ検証結果")
print("="*70)
print(f"{'#':3} {'ラベル':<42} {'状態':<22} {'rc':3}")
print("-"*70)
for r in results:
    print(f"   {r['label']:<44} {r['status']:<22} {r['returncode']:3}")
    if r['status'] in ("ERROR", "SHOULD_HAVE_ERRORED"):
        print(f"     stderr: {r['stderr'][:150]}")
    if r['status'] == "EXPECTED_ERROR":
        print(f"     (想定通りのエラー)")
    # 特定のパターンの追加情報
    if r['report']:
        rp = r['report']
        if "判定" in r['label'] or "有意" in r['label']:
            if "仮説を支持する（" in rp:
                print(f"     判定: 仮説を支持する（B>A）")
            elif "条件Aのほうが有意" in rp or "条件A" in rp:
                print(f"     判定: 条件Aの方が有意に高かった")
            elif "得られなかった" in rp:
                print(f"     判定: 仮説を支持する結果は得られなかった")
        if "#20" in r['label'] or "分散0" in r['label']:
            if "W = NaN" in rp or "同点除外" in rp:
                print(f"     全員同点: WはNaN、正常処理")
        if "天井" in r['label']:
            if "天井効果" in rp or "⚠" in rp:
                print(f"     天井効果警告あり ✓")
            else:
                print(f"     天井効果警告なし ✗")
        if "切り替え" in r['label']:
            if "satisfaction" in rp and "切り替え" in rp:
                print(f"     satisfaction に切り替え ✓")
        if "5人未満" in r['label']:
            if "記述統計のみ" in rp or "5人未満" in rp:
                print(f"     記述統計のみ ✓")
        if "#17" in r['label'] and "空欄" in r['label']:
            # 空欄氏名が「除外」されているか確認
            if "除外" in rp:
                print(f"     空欄氏名を除外 ✓")
            else:
                print(f"     空欄氏名の扱い要確認")

print("="*70)
