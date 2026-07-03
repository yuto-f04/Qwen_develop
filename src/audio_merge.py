import os
from typing import List, Tuple

import numpy as np
import soundfile as sf


def merge_audio_files(
    file_silence_pairs: List[Tuple[str, int]],
    output_path: str,
) -> str:
    """音声ファイル群を可変長の無音を挟みながら結合する (CPUのみ)。

    file_silence_pairs: (ファイルパス, 後続無音ms) のリスト。
    各フレーズの後に指定ミリ秒の無音を挿入する。最後の要素の後は無音なし。
    """
    if not file_silence_pairs:
        raise ValueError("file_silence_pairs が空です。")

    segments = []
    sr = None
    for path, _ in file_silence_pairs:
        data, file_sr = sf.read(path)
        if sr is None:
            sr = file_sr
        segments.append(data)

    first = segments[0]
    parts = []
    for i, seg in enumerate(segments):
        parts.append(seg)
        if i < len(segments) - 1:
            _, silence_ms = file_silence_pairs[i]
            n_samples = int(sr * silence_ms / 1000)
            if first.ndim == 1:
                silence = np.zeros(n_samples, dtype=first.dtype)
            else:
                silence = np.zeros((n_samples, first.shape[1]), dtype=first.dtype)
            parts.append(silence)

    merged = np.concatenate(parts, axis=0)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    sf.write(output_path, merged, sr)
    return output_path
