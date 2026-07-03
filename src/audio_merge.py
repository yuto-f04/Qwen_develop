import os
from typing import List

import numpy as np
import soundfile as sf

from src.config import SILENCE_MS


def merge_audio_files(
    file_list: List[str],
    output_path: str,
    silence_ms: int = SILENCE_MS,
) -> str:
    """音声ファイル群を、各ファイルの間に無音を挟みながら結合する (CPUのみ)。

    file_list の順番で結合し、ファイル間に silence_ms ミリ秒の無音を挿入する。
    最後のファイルの後には無音を挿入しない。
    """
    segments = []
    sr = None

    for path in file_list:
        data, file_sr = sf.read(path)
        if sr is None:
            sr = file_sr
        segments.append(data)

    if not segments:
        raise ValueError("file_list が空です。")

    silence_samples = int(sr * silence_ms / 1000)
    first = segments[0]
    if first.ndim == 1:
        silence = np.zeros(silence_samples, dtype=first.dtype)
    else:
        silence = np.zeros((silence_samples, first.shape[1]), dtype=first.dtype)

    parts = []
    for i, seg in enumerate(segments):
        parts.append(seg)
        if i < len(segments) - 1:
            parts.append(silence)

    merged = np.concatenate(parts, axis=0)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    sf.write(output_path, merged, sr)
    return output_path
