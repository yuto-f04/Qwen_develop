import os
import shutil
import subprocess

from src.config import MAX_REF_SECONDS, WHISPER_MODEL_SIZE


def download_audio(youtube_url: str, output_path: str, cookies_path: str = None) -> str:
    """yt-dlp で YouTube から音声をダウンロードする。

    cookies_path: YouTube のログイン Cookie ファイル (cookies.txt)。
                  Colab など bot 判定される環境では必須。
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    cmd = [
        "yt-dlp", "-x", "--audio-format", "wav",
        "--extractor-args", "youtube:player_client=android,web",
        "-o", output_path,
    ]
    if cookies_path:
        cmd += ["--cookies", cookies_path]
    cmd.append(youtube_url)
    subprocess.run(cmd, check=True)
    return output_path


def remove_bgm(input_path: str, output_path: str) -> str:
    """Demucs を使って BGM/ノイズを除去しボーカルのみ抽出する (GPU依存)。

    Demucs は -o で指定したディレクトリの下に
    htdemucs/{入力ファイル名}/vocals.wav を生成するため、
    処理後に output_path へ移動する。
    """
    out_dir = os.path.dirname(os.path.abspath(output_path))
    os.makedirs(out_dir, exist_ok=True)
    cmd = ["python", "-m", "demucs", "--two-stems=vocals", "-o", out_dir, input_path]
    subprocess.run(cmd, check=True)

    # Demucs の実際の出力先: out_dir/htdemucs/{input_stem}/vocals.wav
    input_stem = os.path.splitext(os.path.basename(input_path))[0]
    demucs_out = os.path.join(out_dir, "htdemucs", input_stem, "vocals.wav")
    shutil.move(demucs_out, output_path)
    return output_path


def transcribe(audio_path: str) -> str:
    """Whisper で音声を文字起こしする (GPU推奨)。"""
    import whisper  # GPU依存 - 関数内でのみインポート

    model = whisper.load_model(WHISPER_MODEL_SIZE)
    result = model.transcribe(audio_path, language="ja")
    return result["text"]


def trim_reference_audio(
    input_path: str,
    output_path: str,
    max_seconds: int = MAX_REF_SECONDS,
) -> str:
    """参照音声を指定秒数にトリミングする (CPUのみ)。

    max_seconds 以下の場合もそのまま output_path に書き出す。
    """
    import soundfile as sf  # CPU のみ

    data, sr = sf.read(input_path)
    max_samples = int(max_seconds * sr)
    if len(data) > max_samples:
        data = data[:max_samples]
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    sf.write(output_path, data, sr)
    return output_path
