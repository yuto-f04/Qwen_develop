"""YouTube音声ダウンロードツール（ローカルPC専用）。

起動: python download_tool.py  または  download_tool.bat をダブルクリック
YouTube URLを貼り付けてボタンを押すだけで最初の10秒をWAVとして output/ に保存する。
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
    ffmpeg_exe = os.path.join(FFMPEG_PATH, "ffmpeg.exe")

    # 1. フルダウンロード（--download-sections は 403 になるため使わない）
    status_var.set("ダウンロード中... (1/2) 音声を取得しています")
    tmp_path = os.path.join(OUTPUT_DIR, "%(title)s_full.%(ext)s")
    dl_cmd = [
        "yt-dlp", "-x", "--audio-format", "wav",
        "--ffmpeg-location", FFMPEG_PATH,
        "--extractor-args", "youtube:player_client=android,web",
        "-o", tmp_path,
        url.strip(),
    ]
    result = subprocess.run(dl_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")

    if result.returncode != 0:
        status_var.set(f"❌ ダウンロードエラー:\n{result.stderr[-400:]}")
        btn.config(state="normal", text="ダウンロード（10秒）")
        return

    # ダウンロードされた _full.wav を探す
    full_files = sorted(
        [f for f in os.listdir(OUTPUT_DIR) if f.endswith("_full.wav")],
        key=lambda f: os.path.getmtime(os.path.join(OUTPUT_DIR, f)),
    )
    if not full_files:
        status_var.set("❌ ダウンロードしたWAVが見つかりませんでした。")
        btn.config(state="normal", text="ダウンロード（10秒）")
        return

    full_path = os.path.join(OUTPUT_DIR, full_files[-1])
    # 出力ファイル名: タイトルから "_full" を除いたもの
    out_name = full_files[-1].replace("_full.wav", ".wav")
    out_path = os.path.join(OUTPUT_DIR, out_name)

    # 2. ffmpeg で最初の10秒だけ切り取る
    status_var.set("トリミング中... (2/2) 最初の10秒を切り取っています")
    trim_cmd = [
        ffmpeg_exe, "-y",
        "-i", full_path,
        "-t", "10",
        "-acodec", "copy",
        out_path,
    ]
    trim_result = subprocess.run(trim_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")

    # 一時ファイルを削除
    try:
        os.remove(full_path)
    except OSError:
        pass

    if trim_result.returncode != 0:
        status_var.set(f"❌ トリミングエラー:\n{trim_result.stderr[-400:]}")
    else:
        status_var.set(
            f"✅ 保存完了!\n\nファイル: {out_name}\n\n"
            "次のステップ:\n"
            "  1. output フォルダが開くので WAV ファイルをコピー\n"
            "  2. Colab の Gradio UI (Step 1) にアップロード"
        )
        os.startfile(OUTPUT_DIR)

    btn.config(state="normal", text="ダウンロード（10秒）")


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
    root.geometry("560x380")
    root.resizable(False, False)

    big = tkfont.Font(size=13, weight="bold")
    med = tkfont.Font(size=11)

    tk.Label(root, text="YouTube 音声ダウンロード（10秒）", font=big, pady=14).pack()
    tk.Label(root, text="URLを貼り付けてボタンを押してください", font=med, fg="#555").pack()

    url_var = tk.StringVar()
    entry = tk.Entry(root, textvariable=url_var, font=med, width=55)
    entry.pack(pady=10, padx=20)
    entry.focus()

    status_var = tk.StringVar(value="待機中...")
    btn = tk.Button(root, text="ダウンロード（10秒）", font=big,
                    bg="#1a73e8", fg="white", relief="flat",
                    padx=12, pady=8)
    btn.config(command=lambda: start_download(url_var, status_var, btn))
    btn.pack(pady=6)

    # Enterキーでも起動
    root.bind("<Return>", lambda _: start_download(url_var, status_var, btn))

    status_label = tk.Label(root, textvariable=status_var, font=med,
                            justify="left", wraplength=520,
                            fg="#333", pady=12, padx=20)
    status_label.pack()

    root.mainloop()


if __name__ == "__main__":
    build_ui()
