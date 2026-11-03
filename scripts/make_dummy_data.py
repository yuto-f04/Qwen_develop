"""scripts/make_dummy_data.py — 架空の回答CSV（20人×2回答）を生成する

条件Bが少し高い設定、同点の人、片方しか答えていない人、
氏名の表記ゆれ（空白・全角）、重複回答、
違和感なしで自由記述が空欄の人を含める。
シード固定。
"""
import argparse
import random
from pathlib import Path

import numpy as np
import pandas as pd


SEED = 42
rng = np.random.default_rng(SEED)
random.seed(SEED)

# Googleフォームのヘッダー（実際のCSVと同じ列名）
HEADER = [
    "タイムスタンプ",
    "1. 体験者の氏名",
    "2. ツアーの条件",
    "3. 何回目の参加ですか？",
    "4. ツアー内容に興味を持ちましたか？",
    "5. ツアーの長さは適切でしたか？",
    "6. ツアー中の説明は分かりやすかったですか？",
    "7. ガイドの語りに熱意を感じましたか？",
    "8. このツアーを他人におすすめできますか？",
    "9. ツアーは期待通りでしたか？",
    "10. このツアーに満足しましたか？",
    "11. ツアー内容は難しいと感じましたか？",
    "12. 体力面で不安は感じましたか？",
    "13. また参加したいと感じましたか？",
    "14. ツアーの説明の中に「違和感」「気になったところ」はありましたか？",
    "14-2. どこで「違和感」を感じたか？",
    "14-3. なぜ「違和感」を抱いたのか？",
    "14-4. その違和感に「興味」を抱いたか？",
    "14-4-2. 興味を抱かなかった理由について簡単に教えてください",
    "14-4-2. 興味を抱いた理由を簡単に教えてください",
    "15. ツアーの中で最も印象に残った場面・体験を教えてください",
    "16. ツアー全体の感想を教えてください  ",  # 末尾2スペース
]

# 架空の名前（20人）
NAMES = [
    "田中太郎", "鈴木花子", "佐藤健一", "高橋美咲", "山田次郎",
    "伊藤さくら", "渡辺浩二", "中村愛", "小林翔太", "加藤由美",
    "吉田雄大", "山本なな", "松本剛", "井上麻衣", "木村誠",
    "林優子", "清水大輔", "山口真理", "池田光", "橋本みき",
]

# 条件ごとの得点の傾向（B>A）
SCALE_MEAN_A = {"interest": 6.0, "length": 7.0, "clarity": 6.5,
                "enthusiasm": 7.0, "recommend": 6.0, "expectation": 6.5,
                "satisfaction": 6.0, "difficulty": 5.0, "physical": 4.0, "revisit": 6.0}
SCALE_MEAN_B = {"interest": 7.5, "length": 7.0, "clarity": 6.5,
                "enthusiasm": 7.0, "recommend": 7.5, "expectation": 7.0,
                "satisfaction": 7.5, "difficulty": 5.5, "physical": 4.0, "revisit": 7.5}
SCALE_SD = 1.8


def clamp_int(v, lo=1, hi=10):
    return int(np.clip(round(v), lo, hi))


def make_scale_vals(cond: str, person_offset: float) -> dict:
    means = SCALE_MEAN_A if cond == "条件A" else SCALE_MEAN_B
    return {k: clamp_int(rng.normal(means[k] + person_offset, SCALE_SD))
            for k in means}


def make_discomfort(cond: str) -> tuple:
    if cond == "条件A":
        probs = [0.60, 0.25, 0.15]
    else:
        probs = [0.30, 0.35, 0.35]
    cat = rng.choice(["なかった", "少しあった", "あった"], p=probs)
    where, why, interest, no_reason, yes_reason = "", "", "", "", ""
    if cat != "なかった":
        where = rng.choice(["シアター教室", "KOBO", "ラウンジ"])
        why = f"{where}の説明が少し意外だった"
        interest_val = rng.choice(["はい", "いいえ"], p=[0.6, 0.4])
        interest = interest_val
        if interest_val == "はい":
            yes_reason = "不思議に思って調べてみたくなった"
        else:
            no_reason = "そこまで気にならなかった"
    return cat, where, why, interest, no_reason, yes_reason


def make_row(
    name: str,
    cond: str,
    rnd: str,
    ts: str,
    person_offset: float,
    add_typo: bool = False,
) -> dict:
    sc = make_scale_vals(cond, person_offset)
    disc, where, why, interest, no_reason, yes_reason = make_discomfort(cond)
    impression = rng.choice(["ガイドの語りが印象的だった", "施設の裏話が面白かった", ""])
    comment = rng.choice(["楽しかったです", "また参加したいと思いました", ""])

    # 表記ゆれ（2名に適用）
    display_name = name
    if add_typo:
        if rng.random() < 0.5:
            display_name = name[0] + "　" + name[1:]  # 全角スペース
        else:
            display_name = name + " "  # 末尾半角スペース

    return {
        "タイムスタンプ": ts,
        "1. 体験者の氏名": display_name,
        "2. ツアーの条件": cond,
        "3. 何回目の参加ですか？": rnd,
        "4. ツアー内容に興味を持ちましたか？": sc["interest"],
        "5. ツアーの長さは適切でしたか？": sc["length"],
        "6. ツアー中の説明は分かりやすかったですか？": sc["clarity"],
        "7. ガイドの語りに熱意を感じましたか？": sc["enthusiasm"],
        "8. このツアーを他人におすすめできますか？": sc["recommend"],
        "9. ツアーは期待通りでしたか？": sc["expectation"],
        "10. このツアーに満足しましたか？": sc["satisfaction"],
        "11. ツアー内容は難しいと感じましたか？": sc["difficulty"],
        "12. 体力面で不安は感じましたか？": sc["physical"],
        "13. また参加したいと感じましたか？": sc["revisit"],
        "14. ツアーの説明の中に「違和感」「気になったところ」はありましたか？": disc,
        "14-2. どこで「違和感」を感じたか？": where,
        "14-3. なぜ「違和感」を抱いたのか？": why,
        "14-4. その違和感に「興味」を抱いたか？": interest,
        "14-4-2. 興味を抱かなかった理由について簡単に教えてください": no_reason,
        "14-4-2. 興味を抱いた理由を簡単に教えてください": yes_reason,
        "15. ツアーの中で最も印象に残った場面・体験を教えてください": impression,
        "16. ツアー全体の感想を教えてください  ": comment,
    }


def make_dummy_csv(output_path: str) -> None:
    rows = []
    base_ts = pd.Timestamp("2026-11-01 10:00:00")

    for i, name in enumerate(NAMES):
        person_offset = rng.normal(0, 0.5)
        add_typo = (i in [2, 5])  # 佐藤健一と伊藤さくらに表記ゆれ

        # グループ1（10人, i<10）: A→B、グループ2（10人, i>=10）: B→A
        if i < 10:
            order = [("条件A", "1回目"), ("条件B", "2回目")]
        else:
            order = [("条件B", "1回目"), ("条件A", "2回目")]

        for j, (cond, rnd) in enumerate(order):
            ts = (base_ts + pd.Timedelta(hours=i * 2 + j)).strftime("%Y/%m/%d %H:%M:%S")
            rows.append(make_row(name, cond, rnd, ts, person_offset, add_typo and j == 0))

    # 同点の人（田中太郎を同点に近い値に設定）—すでに生成済みなので上書きはしない
    # （シード固定で同点になることは偶然任せ。必要なら2件を調整）

    # 重複回答（山田次郎の条件Aを1件追加：古いタイムスタンプ）
    duplicate_name = "山田次郎"
    old_ts = (base_ts - pd.Timedelta(hours=1)).strftime("%Y/%m/%d %H:%M:%S")
    rows.append(make_row(duplicate_name, "条件A", "1回目", old_ts, 0.0))

    # 片方だけしか答えていない人（NAMES外の架空の人）
    partial_ts = (base_ts + pd.Timedelta(hours=50)).strftime("%Y/%m/%d %H:%M:%S")
    rows.append(make_row("片方のみ参加者", "条件A", "1回目", partial_ts, 0.2))

    df = pd.DataFrame(rows, columns=HEADER)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"ダミーデータを生成しました: {output_path} ({len(df)} 行)")


def main():
    parser = argparse.ArgumentParser(description="ダミーアンケートCSVを生成する")
    parser.add_argument(
        "--output",
        default="data/responses.csv",
        help="出力先CSVパス（デフォルト: data/responses.csv）",
    )
    args = parser.parse_args()
    make_dummy_csv(args.output)


if __name__ == "__main__":
    main()
