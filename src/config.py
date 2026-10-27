import os

# 音声結合時に挟む無音の長さ (ミリ秒)
SILENCE_MS = 400        # 句点(。！？)後

# 参照音声の最大秒数 (これを超えたらトリミング)
MAX_REF_SECONDS = 10

# Whisper モデルサイズ（large-v3 を推奨。base は日本語精度が低い）
WHISPER_MODEL_SIZE = "large-v3"

# Qwen3-TTS モデルID
TTS_MODEL_ID = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"

# TTS 生成パラメータ
TTS_SEED = 42           # 再現性のために固定
TTS_TEMPERATURE = 0.7   # 公式デフォルト(0.9)より少し低めで安定

# 出力ディレクトリ
OUTPUT_DIR = "output"
SENTENCES_DIR = os.path.join(OUTPUT_DIR, "sentences")
TRIMMED_AUDIO_PATH = os.path.join(OUTPUT_DIR, "trimmed_ref.wav")
FINAL_OUTPUT_PATH = os.path.join(OUTPUT_DIR, "tour_guide.wav")

# デフォルト参照音声パス
REF_AUDIO_PATH = "clean_audio1.wav"

# UI 状態の保存先
UI_STATE_PATH = os.path.join(OUTPUT_DIR, "ui_state.json")
