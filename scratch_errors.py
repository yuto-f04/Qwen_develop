"""クラッシュする意地悪ケースのエラー詳細確認"""
import io, os, sys, subprocess, tempfile
from pathlib import Path

PYTHON = sys.executable
BASE_DIR = Path(__file__).parent

HEADER = (
    "タイムスタンプ,1. 体験者の氏名,2. ツアーの条件,3. 何回目の参加ですか？,"
    "4. ツアー内容に興味を持ちましたか？,5. ツアーの長さは適切でしたか？,"
    "6. ツアー中の説明は分かりやすかったですか？,7. ガイドの語りに熱意を感じましたか？,"
    "8. このツアーを他人におすすめできますか？,9. ツアーは期待通りでしたか？,"
    "10. このツアーに満足しましたか？,11. ツアー内容は難しいと感じましたか？,"
    "12. 体力面で不安は感じましたか？,13. また参加したいと感じましたか？,"
    "14. ツアーの説明の中に「違和感」「気になったところ」はありましたか？,"
    "14-2. どこで「違和感」を感じたか？,14-3. なぜ「違和感」を抱いたのか？,"
    "14-4. その違和感に「興味」を抱いたか？,"
    "14-4-2. 興味を抱かなかった理由について簡単に教えてください,"
    "14-4-2. 興味を抱いた理由を簡単に教えてください,"
    "15. ツアーの中で最も印象に残った場面・体験を教えてください,"
    "16. ツアー全体の感想を教えてください  "
)

def run(csv_bytes, label):
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        p = d / "r.csv"
        p.write_bytes(csv_bytes)
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        res = subprocess.run([PYTHON, "run_analysis.py", "--input", str(p), "--outdir", str(d/"out")],
                             capture_output=True, text=True, encoding="utf-8", env=env, cwd=str(BASE_DIR))
        print(f"\n=== {label} (rc={res.returncode}) ===")
        if res.returncode != 0:
            # show last 6 lines of stderr
            lines = [l for l in res.stderr.split("\n") if l.strip()]
            for l in lines[-6:]:
                print(f"  {l}")
        else:
            print(f"  OK: {res.stdout[:100]}")

# #3 CP932
try:
    row = "2026/11/01 10:00:00,A,条件A,1回目,7,7,7,7,7,7,7,7,7,7,なかった,,,,,感想"
    row2 = "2026/11/01 11:00:00,A,条件B,2回目,8,8,8,8,8,8,8,8,8,8,なかった,,,,,感想"
    run((HEADER + "\n" + row + "\n" + row2 + "\n").encode("cp932"), "#3 CP932")
except Exception as e:
    print(f"#3 CP932 エンコード失敗: {e}")

# #5 ヘッダーだけ
run((HEADER + "\n").encode("utf-8-sig"), "#5 ヘッダーだけ")

# #6 1件だけ
row1 = "2026/11/01 10:00:00,A,条件A,1回目,7,7,7,7,7,7,7,7,7,7,なかった,,,,,感想"
run((HEADER + "\n" + row1 + "\n").encode("utf-8-sig"), "#6 1件のみ")

# #15 両方とも条件A
row_a1 = "2026/11/01 10:00:00,A,条件A,1回目,7,7,7,7,7,7,7,7,7,7,なかった,,,,,感想"
row_a2 = "2026/11/01 11:00:00,A,条件A,2回目,8,8,8,8,8,8,8,8,8,8,なかった,,,,,感想"
run((HEADER + "\n" + row_a1 + "\n" + row_a2 + "\n").encode("utf-8-sig"), "#15 両方とも条件A")

# #17 氏名空欄のペアになる可能性
row_empty1 = "2026/11/01 10:00:00,,条件A,1回目,7,7,7,7,7,7,7,7,7,7,なかった,,,,,感想"
row_empty2 = "2026/11/01 11:00:00,,条件B,2回目,8,8,8,8,8,8,8,8,8,8,なかった,,,,,感想"
run((HEADER + "\n" + row_empty1 + "\n" + row_empty2 + "\n").encode("utf-8-sig"), "#17b 空欄氏名×2（ペアになるか）")
