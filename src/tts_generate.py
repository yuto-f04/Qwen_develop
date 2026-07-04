import gc
import os
from typing import List

import numpy as np
import soundfile as sf

from src.config import TTS_MODEL_ID

_cached_model = None  # プロセス内でモデルを使い回す


def _load_model():
    """Qwen3-TTS モデルをロードして返す (GPU依存)。

    2回目以降の呼び出しはキャッシュを返すため即座に完了する。
    """
    global _cached_model
    if _cached_model is not None:
        return _cached_model

    import torch  # GPU依存 - 関数内でのみインポート
    import transformers  # GPU依存 - 関数内でのみインポート
    from qwen_tts import Qwen3TTSModel  # GPU依存 - 関数内でのみインポート

    transformers.logging.set_verbosity_error()  # pad_token_id 警告を抑制

    os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
    torch.cuda.empty_cache()
    gc.collect()
    _cached_model = Qwen3TTSModel.from_pretrained(
        TTS_MODEL_ID,
        device_map="auto",
        dtype=torch.float16,
    )
    return _cached_model


def generate_sentence_audio(
    sentence: str,
    reference_audio_path: str,
    output_path: str,
    model=None,
    ref_text: str = "",
) -> str:
    """1文を参照音声の声で Qwen3-TTS により音声生成する (GPU依存)。

    model が None の場合は _load_model() でロードする。
    生成した音声を output_path に書き出し、そのパスを返す。
    """
    import torch  # GPU依存 - 関数内でのみインポート

    if model is None:
        model = _load_model()

    with torch.no_grad():
        wavs, sr = model.generate_voice_clone(
            text=sentence,
            language="Japanese",
            ref_audio=reference_audio_path,
            ref_text=ref_text,
        )

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    sf.write(output_path, wavs[0], sr)
    return output_path


def generate_all(
    sentences: List[str],
    reference_audio_path: str,
    output_dir: str,
    ref_text: str = "",
    progress_callback=None,
) -> List[str]:
    """文リストを順番にすべて音声化し、生成した音声ファイルパスのリストを返す。

    ファイル名は連番で管理する (例: 0001.wav, 0002.wav ...)。
    5文ごとに CUDA キャッシュをクリアしてメモリ使用量を抑える。
    progress_callback(done, total) が渡された場合は1文生成ごとに呼び出す。
    """
    import torch  # GPU依存 - 関数内でのみインポート

    os.makedirs(output_dir, exist_ok=True)
    model = _load_model()
    output_paths = []
    total = len(sentences)

    for i, sentence in enumerate(sentences):
        output_path = os.path.join(output_dir, f"{i + 1:04d}.wav")
        generate_sentence_audio(
            sentence,
            reference_audio_path,
            output_path,
            model=model,
            ref_text=ref_text,
        )
        output_paths.append(output_path)

        if progress_callback:
            progress_callback(i + 1, total)

        if i % 5 == 0:
            torch.cuda.empty_cache()
            gc.collect()

    return output_paths
