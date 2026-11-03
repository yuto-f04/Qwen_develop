"""意地悪データ点検の続き（エンコードエラー回避版）"""
import io
import os
import sys
import subprocess
import tempfile
from pathlib import Path

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

def run_check(csv_content: bytes, label: str, expect_error=False, aliases=None):
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
        return ok, result.stdout, result.stderr[:400], report_text


def report(label, ok, stdout, stderr, report_txt, notes=""):
    status = "OK" if ok else "ERROR"
    print(f"[{status}] {label}")
    if not ok:
        # show first meaningful line of error
        err_lines = [l for l in stderr.split("\n") if l.strip() and "File" not in l and "Traceback" not in l]
        if err_lines:
            print(f"  ERR: {err_lines[0][:120]}")
    if notes:
        print(f"  NOTE: {notes}")


# #3 CP932
try:
    content_cp932 = (HEADER_UTF8 + "\n" + base_row("A","条件A","1回目") + "\n" + base_row("A","条件B","2回目") + "\n").encode("cp932")
    ok, stdout, stderr, rpt = run_check(content_cp932, "#3 CP932")
    report("#3 CP932/Shift-JIS", ok, stdout, stderr, rpt, "UnicodeDecodeError で止まるか？")
except UnicodeEncodeError as e:
    print(f"[SKIP] #3 CP932 - スクリプト側でエンコードできない項目あり: {e}")

# #5 ヘッダーだけ
content_hdr = (HEADER_UTF8 + "\n").encode("utf-8-sig")
ok, stdout, stderr, rpt = run_check(content_hdr, "#5 ヘッダーだけ")
report("#5 ヘッダーだけ（0件）", ok, stdout, stderr, rpt)

# #6 1件だけ
content_1 = (HEADER_UTF8 + "\n" + base_row("A","条件A","1回目") + "\n").encode("utf-8-sig")
ok, stdout, stderr, rpt = run_check(content_1, "#6 1件のみ")
report("#6 1件のみ", ok, stdout, stderr, rpt)

# #15 両方とも条件A
rows_err = [base_row("A","条件A","1回目"), base_row("A","条件A","2回目")]
content_err = (HEADER_UTF8 + "\n" + "\n".join(rows_err) + "\n").encode("utf-8-sig")
ok, stdout, stderr, rpt = run_check(content_err, "#15 両方条件A")
report("#15 両方とも条件A（回答ミス）", ok, stdout, stderr, rpt)

# #17 氏名が空欄（ペアあり）
rows_blank = [base_row("","条件A","1回目"), base_row("A","条件A","1回目"), base_row("A","条件B","2回目")]
content_blank = (HEADER_UTF8 + "\n" + "\n".join(rows_blank) + "\n").encode("utf-8-sig")
ok, stdout, stderr, rpt = run_check(content_blank, "#17 空欄氏名")
report("#17 空欄氏名", ok, stdout, stderr, rpt, "空欄2件がペアになっていないか確認")
if ok:
    if "除外" in rpt:
        print("  -> 空欄氏名が除外リストに載っている")
    else:
        print("  -> 空欄氏名の扱いが不明（除外されていない可能性）")

# #20 全員同点（分散0）
def make_pairs_n(n, vals_a, vals_b):
    rows = []
    for i in range(n):
        nm = f"T{i:02d}"
        rows.append(base_row(nm, "条件A", "1回目", vals_a))
        rows.append(base_row(nm, "条件B", "2回目", vals_b))
    return rows

rows_zero = make_pairs_n(20, "5,5,5,5,5,5,5,5,5,5", "5,5,5,5,5,5,5,5,5,5")
content_zero = (HEADER_UTF8 + "\n" + "\n".join(rows_zero) + "\n").encode("utf-8-sig")
ok, stdout, stderr, rpt = run_check(content_zero, "#20 全員同点（分散0）")
report("#20 全員同点（分散0）", ok, stdout, stderr, rpt)
if ok:
    if "NaN" in rpt and "同点除外" in rpt:
        print("  -> 全員同点として正常処理")
    print(f"  -> 判定文: " + ("仮説を支持する" if "仮説を支持する" in rpt else "得られなかった"))

# #21 全員B>Aで有意
rows_b = make_pairs_n(20, "3,3,3,3,3,3,3,3,3,3", "9,9,9,9,9,9,9,9,9,9")
content_b = (HEADER_UTF8 + "\n" + "\n".join(rows_b) + "\n").encode("utf-8-sig")
ok, stdout, stderr, rpt = run_check(content_b, "#21 全員B>Aで有意")
report("#21 全員B>Aで有意", ok, stdout, stderr, rpt)
if ok:
    if "仮説を支持する（条件B" in rpt:
        print("  -> 判定: B>A 仮説支持 [OK]")
    else:
        print(f"  -> 判定文が想定外: {[l for l in rpt.split(chr(10)) if '仮説' in l or '得られなかった' in l][:3]}")

# #22 A>Bで有意
rows_a = make_pairs_n(20, "9,9,9,9,9,9,9,9,9,9", "3,3,3,3,3,3,3,3,3,3")
content_a = (HEADER_UTF8 + "\n" + "\n".join(rows_a) + "\n").encode("utf-8-sig")
ok, stdout, stderr, rpt = run_check(content_a, "#22 A>Bで有意")
report("#22 A>Bで有意", ok, stdout, stderr, rpt)
if ok:
    if "条件Aのほうが有意" in rpt:
        print("  -> 判定: A>B 仮説不支持 [OK]")
    elif "得られなかった" in rpt:
        print("  -> 判定: 得られなかった [仕様通り]")
    else:
        print(f"  -> 判定文確認: {[l for l in rpt.split(chr(10)) if '仮説' in l][:3]}")

# #23 全員9〜10点（天井）
rows_ceil = make_pairs_n(20, "9,9,9,9,9,9,9,9,9,9", "10,10,10,10,10,10,10,10,10,10")
content_ceil = (HEADER_UTF8 + "\n" + "\n".join(rows_ceil) + "\n").encode("utf-8-sig")
ok, stdout, stderr, rpt = run_check(content_ceil, "#23 全員9〜10点（天井）")
report("#23 全員9〜10点（天井）", ok, stdout, stderr, rpt)
if ok:
    if "天井効果" in rpt or "⚠" in rpt:
        print("  -> 天井効果警告あり [OK]")
    else:
        print("  -> 天井効果警告なし [NG]")

# #26 3人だけ
rows_3 = make_pairs_n(3, "5,5,5,5,5,5,5,5,5,5", "7,7,7,7,7,7,7,7,7,7")
content_3 = (HEADER_UTF8 + "\n" + "\n".join(rows_3) + "\n").encode("utf-8-sig")
ok, stdout, stderr, rpt = run_check(content_3, "#26 3人だけ")
report("#26 3人だけ（小サンプル）", ok, stdout, stderr, rpt)

# #27 グループ2が0人（全員グループ1）
rows_g1 = []
for i in range(10):
    nm = f"T{i:02d}"
    rows_g1.append(base_row(nm, "条件A", "1回目"))
    rows_g1.append(base_row(nm, "条件B", "2回目"))
content_g1 = (HEADER_UTF8 + "\n" + "\n".join(rows_g1) + "\n").encode("utf-8-sig")
ok, stdout, stderr, rpt = run_check(content_g1, "#27 グループ2が0人")
report("#27 グループ2が0人", ok, stdout, stderr, rpt)

# #タイムスタンプ午後表記（NaT になる場合の重複除去への影響確認）
rows_nat = [
    "2026/11/10 午後 1:05:22,TEST01,条件A,1回目,7,7,7,7,7,7,7,7,7,7,なかった,,,,,",
    "2026/11/10 午後 1:06:00,TEST01,条件B,2回目,8,8,8,8,8,8,8,8,8,8,なかった,,,,,",
]
content_nat = (HEADER_UTF8 + "\n" + "\n".join(rows_nat) + "\n").encode("utf-8-sig")
ok, stdout, stderr, rpt = run_check(content_nat, "#9b タイムスタンプ午後表記")
report("#9b タイムスタンプ:午後表記", ok, stdout, stderr, rpt, "NaTになっても止まらないか")

# 同じ人が同じ条件を2回送信 + NaT（重複除去の順序はどうなるか）
rows_dup_nat = [
    "2026/11/10 午後 1:05:22,TEST01,条件A,1回目,5,5,5,5,5,5,5,5,5,5,なかった,,,,,",
    "2026/11/10 13:06:00,TEST01,条件A,1回目,9,9,9,9,9,9,9,9,9,9,なかった,,,,,",
    "2026/11/10 13:07:00,TEST01,条件B,2回目,8,8,8,8,8,8,8,8,8,8,なかった,,,,,",
]
content_dup_nat = (HEADER_UTF8 + "\n" + "\n".join(rows_dup_nat) + "\n").encode("utf-8-sig")
ok, stdout, stderr, rpt = run_check(content_dup_nat, "#9c NaT + 重複")
report("#9c NaT + 重複（重複除去の順序）", ok, stdout, stderr, rpt, "NaTが最新と誤判定されないか")
if ok and "重複" in rpt:
    # 重複除去後の satisfaction_A を確認（9点=新しい方を残したか）
    import pandas as pd
    # Wide CSVは一時ファイルなのでreportのテキストから確認
    if "9" in rpt:
        print("  -> 重複除去の詳細はtidy.csvで確認が必要")
