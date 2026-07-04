import os
import sys
from unittest.mock import MagicMock, patch, call

import numpy as np
import pytest
import soundfile as sf


def make_wav(path: str, duration: float = 1.0, sr: int = 16000) -> str:
    """テスト用のダミー WAV ファイルを作成する。"""
    samples = np.zeros(int(duration * sr), dtype=np.float32)
    sf.write(path, samples, sr)
    return path


class TestDownloadAudio:
    def test_calls_yt_dlp(self):
        from src.audio_preprocess import download_audio

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = download_audio("https://youtube.com/test", "output/test.wav")
            assert mock_run.called
            cmd_args = mock_run.call_args[0][0]
            assert "yt-dlp" in cmd_args
            assert "https://youtube.com/test" in cmd_args

    def test_returns_output_path(self, tmp_path):
        from src.audio_preprocess import download_audio

        out = str(tmp_path / "audio.wav")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = download_audio("https://youtube.com/test", out)
        assert result == out

    def test_uses_cookies_when_provided(self, tmp_path):
        from src.audio_preprocess import download_audio

        cookies = str(tmp_path / "cookies.txt")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            download_audio("https://youtube.com/test", "output/test.wav", cookies_path=cookies)
            cmd_args = mock_run.call_args[0][0]
            assert "--cookies" in cmd_args
            assert cookies in cmd_args

    def test_no_cookies_flag_when_not_provided(self):
        from src.audio_preprocess import download_audio

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            download_audio("https://youtube.com/test", "output/test.wav")
            cmd_args = mock_run.call_args[0][0]
            assert "--cookies" not in cmd_args


class TestRemoveBgm:
    def _make_demucs_output(self, tmp_path, input_stem: str) -> None:
        """Demucs が生成するディレクトリ構造とダミーファイルを作成する。"""
        demucs_dir = tmp_path / "htdemucs" / input_stem
        demucs_dir.mkdir(parents=True)
        (demucs_dir / "vocals.wav").write_bytes(b"dummy_wav")

    def test_calls_demucs(self, tmp_path):
        from src.audio_preprocess import remove_bgm

        self._make_demucs_output(tmp_path, "input")
        out = str(tmp_path / "vocals_out.wav")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = remove_bgm(str(tmp_path / "input.wav"), out)
            cmd_args = mock_run.call_args[0][0]
            assert "demucs" in " ".join(cmd_args)
            assert "--two-stems=vocals" in cmd_args

    def test_moves_vocals_to_output_path(self, tmp_path):
        from src.audio_preprocess import remove_bgm

        self._make_demucs_output(tmp_path, "raw_audio")
        out = str(tmp_path / "vocals_out.wav")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = remove_bgm(str(tmp_path / "raw_audio.wav"), out)
        assert os.path.exists(out)
        assert result == out


class TestTranscribe:
    def test_returns_text(self):
        from src.audio_preprocess import transcribe

        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"text": "こんにちは、世界。"}
        with patch.dict(sys.modules, {"whisper": MagicMock(load_model=MagicMock(return_value=mock_model))}):
            result = transcribe("audio.wav")
        assert result == "こんにちは、世界。"

    def test_calls_transcribe_with_japanese(self):
        from src.audio_preprocess import transcribe

        mock_model = MagicMock()
        mock_model.transcribe.return_value = {"text": "テスト"}
        mock_whisper = MagicMock(load_model=MagicMock(return_value=mock_model))
        with patch.dict(sys.modules, {"whisper": mock_whisper}):
            transcribe("audio.wav")
        mock_model.transcribe.assert_called_once_with("audio.wav", language="ja")


class TestTrimReferenceAudio:
    def test_trims_long_audio(self, tmp_path):
        from src.audio_preprocess import trim_reference_audio

        src = str(tmp_path / "src.wav")
        dst = str(tmp_path / "dst.wav")
        make_wav(src, duration=20.0, sr=16000)

        result = trim_reference_audio(src, dst, max_seconds=5)

        data, sr = sf.read(result)
        assert len(data) / sr <= 5.1

    def test_short_audio_kept_as_is(self, tmp_path):
        from src.audio_preprocess import trim_reference_audio

        src = str(tmp_path / "src.wav")
        dst = str(tmp_path / "dst.wav")
        make_wav(src, duration=3.0, sr=16000)

        result = trim_reference_audio(src, dst, max_seconds=5)

        data, sr = sf.read(result)
        assert abs(len(data) / sr - 3.0) < 0.01

    def test_returns_output_path(self, tmp_path):
        from src.audio_preprocess import trim_reference_audio

        src = str(tmp_path / "src.wav")
        dst = str(tmp_path / "dst.wav")
        make_wav(src, duration=1.0)

        result = trim_reference_audio(src, dst, max_seconds=5)
        assert result == dst

    def test_output_file_created(self, tmp_path):
        from src.audio_preprocess import trim_reference_audio

        src = str(tmp_path / "src.wav")
        dst = str(tmp_path / "dst.wav")
        make_wav(src, duration=1.0)

        trim_reference_audio(src, dst, max_seconds=5)
        assert os.path.exists(dst)
