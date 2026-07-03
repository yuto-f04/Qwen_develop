import re
from typing import List, Tuple

from src.config import SILENCE_COMMA_MS, SILENCE_MS


def split_into_sentences(script: str) -> List[Tuple[str, int]]:
    """台本を句点・読点で分割し、(フレーズ, 後続無音ms) のリストを返す。

    - 句点(。！!?？): SILENCE_MS の無音
    - 読点(、): SILENCE_COMMA_MS の無音
    - 空文字列・空白のみの要素は除去する
    """
    cleaned = script.replace("\n", "")
    parts = re.split(r"(?<=[。！!?？、])", cleaned)

    result = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        silence = SILENCE_COMMA_MS if part.endswith("、") else SILENCE_MS
        result.append((part, silence))

    return result
