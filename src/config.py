import os

# 音声結合時に挟む無音の長さ (ミリ秒)
SILENCE_MS = 400

# 参照音声の最大秒数 (これを超えたらトリミング)
MAX_REF_SECONDS = 10

# Whisper モデルサイズ
WHISPER_MODEL_SIZE = "base"

# Qwen3-TTS モデルID
TTS_MODEL_ID = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"

# 出力ディレクトリ
OUTPUT_DIR = "output"
SENTENCES_DIR = os.path.join(OUTPUT_DIR, "sentences")
TRIMMED_AUDIO_PATH = os.path.join(OUTPUT_DIR, "trimmed_ref.wav")
FINAL_OUTPUT_PATH = os.path.join(OUTPUT_DIR, "tour_guide.wav")

# デフォルト参照音声パス
REF_AUDIO_PATH = "clean_audio1.wav"
