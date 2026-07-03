"""Qwen3-TTS 推論部のテスト。

GPU/モデルは unittest.mock でモック化し、入出力の形式のみを検証する。
実際の推論確認は Colab で行う。
"""
import os
import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import soundfile as sf

DUMMY_SR = 24000
DUMMY_WAV = np.zeros(DUMMY_SR, dtype=np.float32)  # 1秒のダミー音声


def _make_torch_mock() -> MagicMock:
    """torch.no_grad() コンテキストマネージャをモックする。"""
    mock_torch = MagicMock()
    # MagicMock は __enter__/__exit__ を自動生成するので追加設定不要
    return mock_torch


def _make_model_mock() -> MagicMock:
    model = MagicMock()
    model.generate_voice_clone.return_value = ([DUMMY_WAV.copy()], DUMMY_SR)
    return model


class TestGenerateSentenceAudio:
    def test_saves_wav_file(self, tmp_path):
        from src.tts_generate import generate_sentence_audio

        out = str(tmp_path / "out.wav")
        model = _make_model_mock()

        with patch.dict(sys.modules, {"torch": _make_torch_mock()}):
            result = generate_sentence_audio("こんにちは。", "ref.wav", out, model=model)

        assert result == out
        assert os.path.exists(out)

    def test_audio_content_matches_model_output(self, tmp_path):
        from src.tts_generate import generate_sentence_audio

        out = str(tmp_path / "out.wav")
        model = _make_model_mock()

        with patch.dict(sys.modules, {"torch": _make_torch_mock()}):
            generate_sentence_audio("こんにちは。", "ref.wav", out, model=model)

        data, sr = sf.read(out)
        assert len(data) == DUMMY_SR
        assert sr == DUMMY_SR

    def test_calls_model_with_correct_args(self, tmp_path):
        from src.tts_generate import generate_sentence_audio

        out = str(tmp_path / "out.wav")
        model = _make_model_mock()

        with patch.dict(sys.modules, {"torch": _make_torch_mock()}):
            generate_sentence_audio(
                "こんにちは。", "ref.wav", out, model=model, ref_text="テスト"
            )

        model.generate_voice_clone.assert_called_once_with(
            text="こんにちは。",
            language="Japanese",
            ref_audio="ref.wav",
            ref_text="テスト",
        )

    def test_creates_output_dir(self, tmp_path):
        from src.tts_generate import generate_sentence_audio

        out = str(tmp_path / "new_dir" / "out.wav")
        model = _make_model_mock()

        with patch.dict(sys.modules, {"torch": _make_torch_mock()}):
            generate_sentence_audio("テスト。", "ref.wav", out, model=model)

        assert os.path.exists(out)


class TestGenerateAll:
    def test_returns_correct_number_of_paths(self, tmp_path):
        from src.tts_generate import generate_all

        out_dir = str(tmp_path / "sentences")
        sentences = ["こんにちは。", "ありがとう。", "さようなら。"]
        model = _make_model_mock()

        with patch.dict(sys.modules, {"torch": _make_torch_mock(), "qwen_tts": MagicMock()}):
            with patch("src.tts_generate._load_model", return_value=model):
                result = generate_all(sentences, "ref.wav", out_dir)

        assert len(result) == 3

    def test_filenames_are_sequential(self, tmp_path):
        from src.tts_generate import generate_all

        out_dir = str(tmp_path / "sentences")
        sentences = ["文1。", "文2。", "文3。"]
        model = _make_model_mock()

        with patch.dict(sys.modules, {"torch": _make_torch_mock(), "qwen_tts": MagicMock()}):
            with patch("src.tts_generate._load_model", return_value=model):
                result = generate_all(sentences, "ref.wav", out_dir)

        assert os.path.basename(result[0]) == "0001.wav"
        assert os.path.basename(result[1]) == "0002.wav"
        assert os.path.basename(result[2]) == "0003.wav"

    def test_all_files_exist(self, tmp_path):
        from src.tts_generate import generate_all

        out_dir = str(tmp_path / "sentences")
        sentences = ["文1。", "文2。"]
        model = _make_model_mock()

        with patch.dict(sys.modules, {"torch": _make_torch_mock(), "qwen_tts": MagicMock()}):
            with patch("src.tts_generate._load_model", return_value=model):
                result = generate_all(sentences, "ref.wav", out_dir)

        assert all(os.path.exists(p) for p in result)
