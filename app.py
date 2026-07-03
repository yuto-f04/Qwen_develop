"""嘘キャンパスツアーガイド音声生成 Gradio UI。

Colab 上で GPU を使って起動することを前提とする。
ローカルでは `import app` が通ることだけ確認できればよい。
起動: python app.py  (Colab では share=True で公開URL が発行される)
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
    SILENCE_MS,
    TRIMMED_AUDIO_PATH,
)
from src.script_splitter import split_into_sentences


def process_pipeline(
    youtube_url: str,
    ref_audio_file,
    script_text: str,
    progress=gr.Progress(),
) -> str:
    """パイプライン全体を実行し、完成音声ファイルのパスを返す。"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(SENTENCES_DIR, exist_ok=True)

    # 参照音声の取得
    if youtube_url and youtube_url.strip():
        progress(0.05, desc="YouTube から音声をダウンロード中...")
        raw_audio = os.path.join(OUTPUT_DIR, "raw_audio.wav")
        download_audio(youtube_url.strip(), raw_audio)

        progress(0.15, desc="BGM 除去中 (Demucs)...")
        vocal_audio = os.path.join(OUTPUT_DIR, "vocals.wav")
        remove_bgm(raw_audio, vocal_audio)
        ref_source = vocal_audio
    elif ref_audio_file:
        ref_source = ref_audio_file
    else:
        raise ValueError("YouTube URL か参照音声ファイルのどちらかを指定してください。")

    progress(0.25, desc="参照音声をトリミング中...")
    trim_reference_audio(ref_source, TRIMMED_AUDIO_PATH, max_seconds=MAX_REF_SECONDS)

    progress(0.30, desc="参照音声を文字起こし中 (Whisper)...")
    ref_text = transcribe(TRIMMED_AUDIO_PATH)

    progress(0.35, desc="台本を文分割中...")
    sentences = split_into_sentences(script_text)
    if not sentences:
        raise ValueError("台本から文を抽出できませんでした。句点(。！？)が含まれているか確認してください。")

    # TTS 生成 (遅延インポートで GPU 依存を分離)
    from src.tts_generate import generate_all

    progress(0.40, desc=f"TTS 生成中 (全 {len(sentences)} 文)...")
    audio_files = generate_all(sentences, TRIMMED_AUDIO_PATH, SENTENCES_DIR, ref_text=ref_text)

    progress(0.90, desc="音声ファイルを結合中...")
    merge_audio_files(audio_files, FINAL_OUTPUT_PATH, silence_ms=SILENCE_MS)

    progress(1.0, desc="完了！")
    return FINAL_OUTPUT_PATH


def _run_pipeline(youtube_url, ref_audio, script_text):
    try:
        path = process_pipeline(youtube_url, ref_audio, script_text)
        return path, "完了！"
    except Exception as e:
        return None, f"エラー: {e}"


with gr.Blocks(title="嘘ツアーガイド音声生成") as demo:
    gr.Markdown("# 嘘キャンパスツアーガイド音声生成")
    gr.Markdown(
        "YouTube URL または参照音声ファイルと台本テキストを入力して「生成開始」を押してください。"
    )

    with gr.Row():
        with gr.Column():
            youtube_url = gr.Textbox(
                label="YouTube URL（参照音声取得用）",
                placeholder="https://www.youtube.com/watch?v=...",
            )
            ref_audio = gr.Audio(label="または参照音声ファイルをアップロード", type="filepath")
            script_text = gr.Textbox(
                label="台本テキスト",
                lines=12,
                placeholder="ここに台本を貼り付けてください。句点(。！？)で文分割します。",
            )
            run_btn = gr.Button("生成開始", variant="primary")

        with gr.Column():
            output_audio = gr.Audio(label="生成された音声", type="filepath")
            status_box = gr.Textbox(label="ステータス", interactive=False)

    run_btn.click(
        fn=_run_pipeline,
        inputs=[youtube_url, ref_audio, script_text],
        outputs=[output_audio, status_box],
    )

if __name__ == "__main__":
    demo.launch(share=True)
