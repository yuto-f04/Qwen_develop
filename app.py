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


def prepare_reference(youtube_url: str, ref_audio_file, progress=gr.Progress()):
    """参照音声を準備し、クリーン音声と文字起こし結果を返す。

    戻り値:
        clean_audio_path: ダウンロード可能なトリミング済み音声
        ref_text:         Whisper による文字起こし（手で修正可能）
        status:           進捗メッセージ
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if youtube_url and youtube_url.strip():
        progress(0.05, desc="YouTube から音声をダウンロード中...")
        raw_audio = os.path.join(OUTPUT_DIR, "raw_audio.wav")
        download_audio(youtube_url.strip(), raw_audio)

        progress(0.40, desc="BGM・ノイズを除去中 (Demucs)...")
        vocal_audio = os.path.join(OUTPUT_DIR, "vocals.wav")
        remove_bgm(raw_audio, vocal_audio)
        ref_source = vocal_audio

    elif ref_audio_file:
        ref_source = ref_audio_file

    else:
        return None, "", "エラー: YouTube URL か参照音声ファイルのどちらかを指定してください。"

    progress(0.70, desc=f"音声を {MAX_REF_SECONDS} 秒にトリミング中...")
    trim_reference_audio(ref_source, TRIMMED_AUDIO_PATH, max_seconds=MAX_REF_SECONDS)

    progress(0.85, desc="Whisper で文字起こし中...")
    ref_text = transcribe(TRIMMED_AUDIO_PATH)

    progress(1.0, desc="完了。クリーン音声を確認し、文字起こしを修正してください。")
    return TRIMMED_AUDIO_PATH, ref_text, "完了！クリーン音声を確認・ダウンロードし、文字起こしを修正してから「音声生成開始」を押してください。"


def generate_audio(script_text: str, ref_text: str, progress=gr.Progress()):
    """修正済み ref_text を使って TTS 生成 → 結合する。"""
    if not ref_text.strip():
        return None, "エラー: 文字起こしテキストが空です。先に「文字起こし実行」を押してください。"
    if not script_text.strip():
        return None, "エラー: 台本テキストが空です。"

    os.makedirs(SENTENCES_DIR, exist_ok=True)

    progress(0.05, desc="台本を文分割中...")
    sentences = split_into_sentences(script_text)
    if not sentences:
        return None, "エラー: 台本から文を抽出できませんでした。句点(。！？)が含まれているか確認してください。"

    from src.tts_generate import generate_all

    progress(0.10, desc=f"TTS 生成中 (全 {len(sentences)} 文)...")
    audio_files = generate_all(
        sentences, TRIMMED_AUDIO_PATH, SENTENCES_DIR, ref_text=ref_text
    )

    progress(0.95, desc="音声ファイルを結合中...")
    merge_audio_files(audio_files, FINAL_OUTPUT_PATH, silence_ms=SILENCE_MS)

    progress(1.0, desc="完了！")
    return FINAL_OUTPUT_PATH, f"完了！ {len(sentences)} 文を生成しました。"


with gr.Blocks(title="嘘ツアーガイド音声生成") as demo:
    gr.Markdown("# 嘘キャンパスツアーガイド音声生成")

    with gr.Row():
        # 左カラム：入力
        with gr.Column():
            gr.Markdown("## Step 1: 参照音声の準備")
            youtube_url = gr.Textbox(
                label="YouTube URL（BGM除去 → 10秒クリップを自動生成）",
                placeholder="https://www.youtube.com/watch?v=...",
            )
            ref_audio = gr.Audio(
                label="または手元の音声ファイルをアップロード",
                type="filepath",
            )
            transcribe_btn = gr.Button("▶ 文字起こし実行（クリーン音声を生成）", variant="secondary")

            gr.Markdown("## Step 2: 台本を入力して音声生成")
            ref_text_box = gr.Textbox(
                label="参照音声の文字起こし（自動入力。間違っていれば手で修正してください）",
                lines=4,
                placeholder="先に「文字起こし実行」を押すと自動入力されます。",
            )
            script_text = gr.Textbox(
                label="台本テキスト",
                lines=12,
                placeholder="ここに台本を貼り付けてください。句点(。！？)で文分割します。",
            )
            generate_btn = gr.Button("▶ 音声生成開始", variant="primary")

        # 右カラム：出力
        with gr.Column():
            status_box = gr.Textbox(label="ステータス", interactive=False, lines=2)
            clean_audio_out = gr.Audio(
                label="クリーン参照音声（10秒）← 確認・ダウンロード用",
                type="filepath",
            )
            output_audio = gr.Audio(
                label="生成された完成音声 ← ダウンロード用",
                type="filepath",
            )

    transcribe_btn.click(
        fn=prepare_reference,
        inputs=[youtube_url, ref_audio],
        outputs=[clean_audio_out, ref_text_box, status_box],
    )

    generate_btn.click(
        fn=generate_audio,
        inputs=[script_text, ref_text_box],
        outputs=[output_audio, status_box],
    )

if __name__ == "__main__":
    demo.launch(share=True)
