import re
from typing import List, Tuple

from src.config import SILENCE_MS


def split_into_sentences(script: str) -> List[Tuple[str, int]]:
    """台本を句点(。！!?？)で分割し、(文, 後続無音ms) のリストを返す。

    読点(、)では分割しない。文の途中の間はモデルに任せる。
    空文字列・空白のみの要素は除去する。
    """
    cleaned = script.replace("\n", "")
    parts = re.split(r"(?<=[。！!?？])", cleaned)

    result = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        result.append((part, SILENCE_MS))

    return result
