import re
from typing import List


def split_into_sentences(script: str) -> List[str]:
    """台本を句点(。)・感嘆符(！)・疑問符(？)の直後で分割する。

    - 区切り文字は各文の末尾に残す
    - 読点(、)では分割しない
    - 空文字列・空白のみの要素は除去する
    """
    cleaned = script.replace("\n", "")
    parts = re.split(r"(?<=[。！!?？])", cleaned)
    return [s.strip() for s in parts if s.strip()]
