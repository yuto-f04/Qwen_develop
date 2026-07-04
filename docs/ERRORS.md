# ERRORS.md — エラー記録

新しいタスクを始める前に必ずこのファイルを読み込むこと。
エラーが解決したら以下のテンプレートに従って追記する。

---

## テンプレート

```
## [YYYY-MM-DD] エラータイトル（一行で内容がわかるもの）

- **発生状況**: どの環境で、何の操作をしていたか
- **エラーメッセージ**:
  ```
  実際のエラーメッセージをそのまま貼る
  ```
- **原因**: なぜこのエラーが起きたか
- **解決策**: どのファイルをどう変更したか
- **再発防止**: 同じエラーを出さないために今後どうするか
```

---

## 記入例

## 2026-07-03 Whisper が FileNotFoundError を出す (ローカル環境)

- **発生状況**: ローカルの VS Code で `Qwen_develop.ipynb` を実行し、
  `whisper_model.transcribe(TRIMMED_AUDIO, language='ja')` を呼んだとき
- **エラーメッセージ**:
  ```
  FileNotFoundError: [WinError 2] 指定されたファイルが見つかりません。
  File "whisper\audio.py", line 58, in load_audio
    out = run(cmd, capture_output=True, check=True).stdout
  ```
- **原因**: Whisper は内部で `ffmpeg` コマンドを subprocess 経由で呼ぶ。
  Windows 環境に ffmpeg がインストールされていないため `FileNotFoundError` が発生した。
- **解決策**: このエラーはローカル実行を想定していないため、`transcribe` 関数の
  GPU 依存テストでは `unittest.mock` でモック化し、実行は Colab に委ねる設計に変更した。
  (`tests/test_audio_preprocess.py` の `TestTranscribe` 参照)
- **再発防止**: GPU/ffmpeg 依存の関数はローカルでは実行しない。
  `import whisper` は `transcribe()` 関数の内側のみで行い、モジュール読み込み時にエラーが出ない設計を維持する。

---

*以降、Colab またはローカルで発生したエラーを都度ここに追記する。*

---

## 2026-07-04 yt-dlp が YouTube の bot 判定でダウンロード失敗 (Colab 環境)

- **発生状況**: Colab 上で Gradio UI を起動し、YouTube URL を入力して「① クリーン音声を生成」を押したとき
- **エラーメッセージ**:
  ```
  ERROR: [youtube] xxxx: Sign in to confirm you're not a bot. Use --cookies-from-browser or --cookies for the authentication.
  subprocess.CalledProcessError: Command '['yt-dlp', ...]' returned non-zero exit status 1.
  ```
- **原因**: Colab の IP アドレスは YouTube から信頼されておらず、ログイン済みセッションの証明なしにダウンロードができない。
- **解決策**:
  1. `download_audio()` に `cookies_path: str = None` 引数を追加し、指定時は `--cookies` フラグを yt-dlp に渡すよう変更 (`src/audio_preprocess.py`)
  2. `app.py` の Step 1 に cookies.txt アップロード UI（Accordion 内）を追加
  3. Chrome 拡張「Get cookies.txt LOCALLY」で YouTube ログイン状態の Cookie をエクスポートし、UI からアップロードすることで認証を通す
- **再発防止**: Colab で YouTube URL を使う場合は cookies.txt が必要。UI の Accordion に手順を明記済み。音声ファイルを直接アップロードすれば cookies 不要で回避もできる。
