import os

import numpy as np
import pytest
import soundfile as sf

from src.audio_merge import merge_audio_files


def make_wav(path: str, duration: float = 1.0, sr: int = 16000, value: float = 0.5) -> str:
    """テスト用のダミー WAV ファイルを作成する。"""
    samples = np.full(int(duration * sr), value, dtype=np.float32)
    sf.write(path, samples, sr)
    return path


class TestMergeAudioFiles:
    def test_merges_two_files(self, tmp_path):
        f1 = make_wav(str(tmp_path / "1.wav"), duration=1.0, sr=16000)
        f2 = make_wav(str(tmp_path / "2.wav"), duration=1.0, sr=16000)
        out = str(tmp_path / "out.wav")

        merge_audio_files([f1, f2], out, silence_ms=400)

        data, sr = sf.read(out)
        # 1s + 0.4s silence + 1s = 2.4s
        expected_samples = int(1.0 * sr) + int(0.4 * sr) + int(1.0 * sr)
        assert abs(len(data) - expected_samples) <= 2

    def test_silent_region_between_files(self, tmp_path):
        sr = 16000
        f1 = make_wav(str(tmp_path / "1.wav"), duration=0.5, sr=sr, value=1.0)
        f2 = make_wav(str(tmp_path / "2.wav"), duration=0.5, sr=sr, value=1.0)
        out = str(tmp_path / "out.wav")

        merge_audio_files([f1, f2], out, silence_ms=200)

        data, _ = sf.read(out)
        # 無音区間: サンプル 0.5s〜0.7s
        mid_start = int(0.5 * sr)
        mid_end = mid_start + int(0.2 * sr)
        assert np.allclose(data[mid_start:mid_end], 0.0, atol=1e-5)

    def test_single_file_no_silence(self, tmp_path):
        f1 = make_wav(str(tmp_path / "1.wav"), duration=1.0, sr=16000)
        out = str(tmp_path / "out.wav")

        merge_audio_files([f1], out, silence_ms=400)

        data, sr = sf.read(out)
        assert abs(len(data) / sr - 1.0) < 0.01

    def test_returns_output_path(self, tmp_path):
        f1 = make_wav(str(tmp_path / "1.wav"))
        out = str(tmp_path / "out.wav")

        result = merge_audio_files([f1], out)
        assert result == out

    def test_output_file_created(self, tmp_path):
        f1 = make_wav(str(tmp_path / "1.wav"))
        out = str(tmp_path / "out.wav")

        merge_audio_files([f1], out)
        assert os.path.exists(out)

    def test_three_files_length(self, tmp_path):
        sr = 16000
        files = [
            make_wav(str(tmp_path / f"{i}.wav"), duration=1.0, sr=sr)
            for i in range(3)
        ]
        out = str(tmp_path / "out.wav")

        merge_audio_files(files, out, silence_ms=300)

        data, _ = sf.read(out)
        # 1s + 0.3s + 1s + 0.3s + 1s = 3.6s
        expected = int(1.0 * sr) * 3 + int(0.3 * sr) * 2
        assert abs(len(data) - expected) <= 2

    def test_raises_on_empty_list(self, tmp_path):
        out = str(tmp_path / "out.wav")
        with pytest.raises(ValueError):
            merge_audio_files([], out)
