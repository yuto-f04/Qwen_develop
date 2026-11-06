"""src/analysis/dummy.py — 実験データのダミー生成"""
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from src import config


def generate_dummy_csv(n_per_group: int = 10, seed: int = 42) -> pd.DataFrame:
    """20人分（グループ1: A→B 10人、グループ2: B→A 10人）のダミーCSVを生成する。

    条件B（嘘あり）の方がエンタメ指標でやや高くなるよう設計。
    列名は実際のGoogleフォームCSVと同一（config.COLUMN_MAP の値）。
    """
    rng = np.random.default_rng(seed)

    names_g1 = [f"架空太郎{i + 1:02d}" for i in range(n_per_group)]
    names_g2 = [f"架空花子{i + 1:02d}" for i in range(n_per_group)]

    base_time = datetime(2026, 11, 20, 10, 0, 0)
    rows = []

    for group, names in [(1, names_g1), (2, names_g2)]:
        for i, name in enumerate(names):
            if group == 1:
                tours = [(config.CONDITION_A, config.ROUND_FIRST),
                         (config.CONDITION_B, config.ROUND_SECOND)]
            else:
                tours = [(config.CONDITION_B, config.ROUND_FIRST),
                         (config.CONDITION_A, config.ROUND_SECOND)]

            for j, (cond, round_) in enumerate(tours):
                is_B = (cond == config.CONDITION_B)
                ts = base_time + timedelta(
                    minutes=(group * n_per_group + i) * 30 + j * 15
                )

                # エンタメ項目（Q4, Q8, Q10, Q13）: 条件Bで+1〜2点
                b_boost = int(rng.integers(1, 3)) if is_B else 0
                base = int(rng.integers(5, 8))

                q4  = int(np.clip(base + b_boost + rng.integers(-1, 2), 1, 10))
                q8  = int(np.clip(base + b_boost + rng.integers(-1, 2), 1, 10))
                q10 = int(np.clip(base + b_boost + rng.integers(-1, 2), 1, 10))
                q13 = int(np.clip(base + b_boost + rng.integers(-1, 2), 1, 10))
                q9  = int(np.clip(base + rng.integers(-1, 2), 1, 10))

                # 条件確認項目（Q5, Q6, Q7, Q11, Q12）: 条件間でほぼ同等
                q5  = int(np.clip(7 + rng.integers(-2, 3), 1, 10))
                q6  = int(np.clip(7 + rng.integers(-2, 3), 1, 10))
                q7  = int(np.clip(7 + rng.integers(-2, 3), 1, 10))
                q11 = int(np.clip(3 + rng.integers(-2, 3), 1, 10))
                q12 = int(np.clip(2 + rng.integers(-2, 3), 1, 10))

                # 違和感: 条件Bで多め
                if is_B:
                    disc = str(rng.choice(config.DISCOMFORT_CATEGORIES, p=[0.25, 0.45, 0.30]))
                else:
                    disc = str(rng.choice(config.DISCOMFORT_CATEGORIES, p=[0.60, 0.30, 0.10]))

                disc_where = disc_why = disc_interest = no_interest_reason = interest_reason = ""
                if disc in config.DISCOMFORT_PRESENT_CATEGORIES:
                    disc_where = "音声のイントネーション"
                    disc_why = "AIっぽい話し方だったから"
                    disc_interest = str(rng.choice(config.DISCOMFORT_INTEREST_CHOICES))
                    if disc_interest == config.DISCOMFORT_INTEREST_CHOICES[1]:  # "いいえ"
                        no_interest_reason = "特に気にならなかったから"
                    else:
                        interest_reason = "なぜそのような説明をするのか気になったから"

                rows.append({
                    config.COLUMN_MAP["timestamp"]:           ts.strftime("%Y/%m/%d %H:%M:%S"),
                    config.COLUMN_MAP["name"]:                name,
                    config.COLUMN_MAP["condition"]:           cond,
                    config.COLUMN_MAP["round"]:               round_,
                    config.COLUMN_MAP["interest"]:            q4,
                    config.COLUMN_MAP["length"]:              q5,
                    config.COLUMN_MAP["clarity"]:             q6,
                    config.COLUMN_MAP["enthusiasm"]:          q7,
                    config.COLUMN_MAP["recommend"]:           q8,
                    config.COLUMN_MAP["expectation"]:         q9,
                    config.COLUMN_MAP["satisfaction"]:        q10,
                    config.COLUMN_MAP["difficulty"]:          q11,
                    config.COLUMN_MAP["physical"]:            q12,
                    config.COLUMN_MAP["revisit"]:             q13,
                    config.COLUMN_MAP["discomfort"]:          disc,
                    config.COLUMN_MAP["discomfort_where"]:    disc_where,
                    config.COLUMN_MAP["discomfort_why"]:      disc_why,
                    config.COLUMN_MAP["discomfort_interest"]: disc_interest,
                    config.COLUMN_MAP["no_interest_reason"]:  no_interest_reason,
                    config.COLUMN_MAP["interest_reason"]:     interest_reason,
                    config.COLUMN_MAP["impression"]:          "印象に残ったシーン（ダミー）",
                    config.COLUMN_MAP["comment"]:             "全体の感想（ダミー）",
                })

    return pd.DataFrame(rows)
