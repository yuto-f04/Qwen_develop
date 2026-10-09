"""YouTube音声ダウンロードツール（ローカルPC専用）。

起動: python download_tool.py  または  download_tool.bat をダブルクリック
YouTube URLを貼り付けてボタンを押すだけでフル音声をWAVとして output/ に保存する。
Gradio の Step 1 でそのファイルをアップロードし、時間範囲を指定してください。
"""
import os
import subprocess
import threading
import tkinter as tk
from tkinter import font as tkfont

FFMPEG_PATH = (
    r"C:\Users\yutof\AppData\Local\Microsoft\WinGet\Packages"
    r"\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe"
    r"\ffmpeg-9.0.2-full_build\bin"
)
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")


def _run_download(url: str, status_var: tk.StringVar, btn: tk.Button) -> None:
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    status_var.set("ダウンロード中... 音声を取得しています（動画の長さによっては数分かかります）")
    out_template = os.path.join(OUTPUT_DIR, "%(title)s.%(ext)s")
    dl_cmd = [
        "yt-dlp", "-x", "--audio-format", "wav",
        "--ffmpeg-location", FFMPEG_PATH,
        "--extractor-args", "youtube:player_client=android,web",
        "-o", out_template,
        url.strip(),
    ]
    result = subprocess.run(dl_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")

    if result.returncode != 0:
        status_var.set(f"❌ ダウンロードエラー:\n{result.stderr[-400:]}")
        btn.config(state="normal", text="ダウンロード（フル）")
        return

    # 保存されたファイルを探す（最新のwav）
    wav_files = sorted(
        [f for f in os.listdir(OUTPUT_DIR) if f.endswith(".wav")],
        key=lambda f: os.path.getmtime(os.path.join(OUTPUT_DIR, f)),
    )
    out_name = wav_files[-1] if wav_files else "（不明）"

    status_var.set(
        f"✅ 保存完了!\n\nファイル: {out_name}\n\n"
        "次のステップ:\n"
        "  1. output フォルダのWAVファイルを Colab の Gradio UI (Step 1) にアップロード\n"
        "  2. 時間範囲を指定してクリーン音声を生成（例: 0:30-0:45, 1:20-1:35）"
    )
    os.startfile(OUTPUT_DIR)
    btn.config(state="normal", text="ダウンロード（フル）")


def start_download(url_var: tk.StringVar, status_var: tk.StringVar, btn: tk.Button) -> None:
    url = url_var.get().strip()
    if not url:
        status_var.set("⚠ URLを入力してください。")
        return
    btn.config(state="disabled", text="ダウンロード中...")
    status_var.set("ダウンロード中... しばらくお待ちください。")
    threading.Thread(target=_run_download, args=(url, status_var, btn), daemon=True).start()


def build_ui() -> None:
    root = tk.Tk()
    root.title("YouTube 音声ダウンロード")
    root.geometry("580x420")
    root.resizable(False, False)

    big = tkfont.Font(size=13, weight="bold")
    med = tkfont.Font(size=11)
    small = tkfont.Font(size=9)

    tk.Label(root, text="YouTube 音声ダウンロード（フル）", font=big, pady=14).pack()
    tk.Label(root, text="URLを貼り付けてボタンを押してください", font=med, fg="#555").pack()
    tk.Label(
        root,
        text="動画全体をダウンロードします。Gradio の Step 1 で時間範囲を指定してください。",
        font=small, fg="#888", wraplength=540,
    ).pack(pady=(0, 6))

    url_var = tk.StringVar()
    entry = tk.Entry(root, textvariable=url_var, font=med, width=55)
    entry.pack(pady=6, padx=20)
    entry.focus()

    status_var = tk.StringVar(value="待機中...")
    btn = tk.Button(root, text="ダウンロード（フル）", font=big,
                    bg="#1a73e8", fg="white", relief="flat",
                    padx=12, pady=8)
    btn.config(command=lambda: start_download(url_var, status_var, btn))
    btn.pack(pady=6)

    root.bind("<Return>", lambda _: start_download(url_var, status_var, btn))

    status_label = tk.Label(root, textvariable=status_var, font=med,
                            justify="left", wraplength=540,
                            fg="#333", pady=12, padx=20)
    status_label.pack()

    root.mainloop()


if __name__ == "__main__":
    build_ui()
