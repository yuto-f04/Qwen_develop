"""嘘キャンパスツアーガイド音声生成 Gradio UI。

Colab 上で GPU を使って起動することを前提とする。
起動: python app.py  (share=True で公開URLが発行される)
"""
import os

import gradio as gr

from src.audio_merge import merge_audio_files
from src.audio_preprocess import (
    download_audio,
    remove_bgm,
    transcribe,
    trim_reference_audio,
)
from src.config import (
    FINAL_OUTPUT_PATH,
    MAX_REF_SECONDS,
    OUTPUT_DIR,
    SENTENCES_DIR,
    TRIMMED_AUDIO_PATH,
)
from src.script_splitter import split_into_sentences
from src.text_normalizer import normalize_for_tts


# ------------------------------------------------------------------ #
#  Step 1: クリーン音声を生成                                          #
# ------------------------------------------------------------------ #
def create_clean_audio(youtube_url: str, ref_audio_file, progress=gr.Progress()):
    """YouTube URL または音声ファイルから BGM を除去し 10 秒にトリミングする。"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if youtube_url and youtube_url.strip():
        progress(0.10, desc="YouTube から音声をダウンロード中...")
        raw_audio = os.path.join(OUTPUT_DIR, "raw_audio.wav")
        download_audio(youtube_url.strip(), raw_audio)

        # Demucs の前に短く切り取る → 全体を処理せずに済むので大幅に高速化
        progress(0.30, desc=f"音声を {MAX_REF_SECONDS} 秒にトリミング中...")
        raw_short = os.path.join(OUTPUT_DIR, "raw_short.wav")
        trim_reference_audio(raw_audio, raw_short, max_seconds=MAX_REF_SECONDS)

        progress(0.50, desc="BGM・ノイズを除去中 (Demucs)...")
        vocal_audio = os.path.join(OUTPUT_DIR, "vocals.wav")
        remove_bgm(raw_short, vocal_audio)
        ref_source = vocal_audio

    elif ref_audio_file:
        ref_source = ref_audio_file

    else:
        return None, "⚠ YouTube URL か音声ファイルのどちらかを指定してください。"

    progress(0.90, desc="クリーン音声を保存中...")
    trim_reference_audio(ref_source, TRIMMED_AUDIO_PATH, max_seconds=MAX_REF_SECONDS)

    progress(1.0, desc="完了")
    return TRIMMED_AUDIO_PATH, "✅ クリーン音声を生成しました。再生して確認してください。"


# ------------------------------------------------------------------ #
#  Step 2: 文字起こし                                                  #
# ------------------------------------------------------------------ #
def run_transcription(progress=gr.Progress()):
    """Step 1 で生成したクリーン音声を Whisper で文字起こしする。"""
    if not os.path.exists(TRIMMED_AUDIO_PATH):
        return "", "⚠ 先に Step 1 でクリーン音声を生成してください。"

    progress(0.3, desc="Whisper で文字起こし中...")
    ref_text = transcribe(TRIMMED_AUDIO_PATH)

    progress(1.0, desc="完了")
    return ref_text, "✅ 文字起こし完了。内容を確認・修正してください。"


# ------------------------------------------------------------------ #
#  Step 3: 音声生成                                                    #
# ------------------------------------------------------------------ #
def generate_audio(script_text: str, ref_text: str, progress=gr.Progress()):
    """台本テキストと文字起こしを使って TTS 音声を生成・結合する。"""
    if not os.path.exists(TRIMMED_AUDIO_PATH):
        return None, "⚠ 先に Step 1 でクリーン音声を生成してください。"
    if not ref_text.strip():
        return None, "⚠ 先に Step 2 で文字起こしを実行してください。"
    if not script_text.strip():
        return None, "⚠ 台本テキストを入力してください。"

    os.makedirs(SENTENCES_DIR, exist_ok=True)

    progress(0.05, desc="台本を文分割中...")
    normalized = normalize_for_tts(script_text)
    segments = split_into_sentences(normalized)
    if not segments:
        return None, "⚠ 台本から文を抽出できませんでした。句点(。！？)が含まれているか確認してください。"

    texts = [t for t, _ in segments]
    silences = [ms for _, ms in segments]

    from src.tts_generate import generate_all

    progress(0.10, desc=f"TTS 生成中 (全 {len(segments)} フレーズ)...")
    audio_files = generate_all(
        texts, TRIMMED_AUDIO_PATH, SENTENCES_DIR, ref_text=ref_text
    )

    progress(0.95, desc="音声ファイルを結合中...")
    merge_audio_files(list(zip(audio_files, silences)), FINAL_OUTPUT_PATH)

    progress(1.0, desc="完了")
    return FINAL_OUTPUT_PATH, f"✅ 完了！ {len(segments)} フレーズを生成しました。"


# ------------------------------------------------------------------ #
#  Gradio UI                                                           #
# ------------------------------------------------------------------ #
css = """
.step-box { border: 1px solid #444; border-radius: 8px; padding: 16px; margin-bottom: 12px; }
"""

with gr.Blocks(title="嘘ツアーガイド音声生成", css=css) as demo:
    gr.Markdown("# 嘘キャンパスツアーガイド音声生成")
    gr.Markdown("3つのステップを順番に実行してください。")

    # ── Step 1 ──────────────────────────────────────────────────────
    with gr.Group(elem_classes="step-box"):
        gr.Markdown("## Step 1　クリーン音声を生成する")
        gr.Markdown("YouTube URL を貼るか、手元の音声ファイルをアップロードしてください。BGM 除去 → 10 秒クリップを自動生成します。")
        with gr.Row():
            youtube_url = gr.Textbox(
                label="YouTube URL",
                placeholder="https://www.youtube.com/watch?v=...",
                scale=3,
            )
            ref_audio = gr.Audio(
                label="または音声ファイルをアップロード",
                type="filepath",
                scale=2,
            )
        clean_btn = gr.Button("① クリーン音声を生成（BGM除去 → 10秒）", variant="secondary")
        with gr.Row():
            clean_audio_out = gr.Audio(
                label="生成されたクリーン音声（再生・ダウンロード）",
                type="filepath",
                scale=3,
            )
            clean_status = gr.Textbox(label="ステータス", interactive=False, scale=2, lines=2)

    # ── Step 2 ──────────────────────────────────────────────────────
    with gr.Group(elem_classes="step-box"):
        gr.Markdown("## Step 2　参照音声を文字起こしする")
        gr.Markdown("Step 1 で生成したクリーン音声を Whisper で文字起こしします。間違っていれば手で直してください。")
        transcribe_btn = gr.Button("② 文字起こし実行", variant="secondary")
        with gr.Row():
            ref_text_box = gr.Textbox(
                label="文字起こし結果（ここを手で修正できます）",
                lines=4,
                placeholder="「② 文字起こし実行」を押すと自動入力されます。",
                scale=3,
            )
            transcribe_status = gr.Textbox(label="ステータス", interactive=False, scale=2, lines=2)

    # ── Step 3 ──────────────────────────────────────────────────────
    with gr.Group(elem_classes="step-box"):
        gr.Markdown("## Step 3　台本から音声を生成する")
        gr.Markdown("台本テキストを貼り付けてください。句点(。！？)で1文ずつ分割して音声を生成します。")
        script_text = gr.Textbox(
            label="台本テキスト",
            lines=12,
            placeholder="ここに台本を貼り付けてください。",
        )
        generate_btn = gr.Button("③ 音声生成開始", variant="primary")
        with gr.Row():
            output_audio = gr.Audio(
                label="完成音声（再生・ダウンロード）",
                type="filepath",
                scale=3,
            )
            generate_status = gr.Textbox(label="ステータス", interactive=False, scale=2, lines=2)

    # ── イベント接続 ─────────────────────────────────────────────────
    clean_btn.click(
        fn=create_clean_audio,
        inputs=[youtube_url, ref_audio],
        outputs=[clean_audio_out, clean_status],
    )
    transcribe_btn.click(
        fn=run_transcription,
        inputs=[],
        outputs=[ref_text_box, transcribe_status],
    )
    generate_btn.click(
        fn=generate_audio,
        inputs=[script_text, ref_text_box],
        outputs=[output_audio, generate_status],
    )

if __name__ == "__main__":
    demo.launch(share=True)
