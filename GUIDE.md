# 嘘ツアーガイド音声生成 — 操作手順書

> **これを見れば一人で全工程できる。上から順に実行するだけ。**

---

## 全体の流れ（5分で把握）

```
① YouTube音声DL    ② Colab起動         ③ Gradio UI操作
  (ローカルPC)        (ブラウザ)           (ブラウザ)
  ↓                   ↓                    ↓
download_tool.bat → colab_runner.ipynb → Step1→Step2→Step3
                                              ↓
                                         tour_guide.wav 完成
```

---

## 事前確認（初回のみ）

以下がインストール済みか確認する。

```powershell
# VSCodeのターミナルで実行
yt-dlp --version
```

`yt-dlp`が見つからない場合：
```powershell
pip install yt-dlp
```

---

## STEP 1｜YouTube から音声をダウンロードする（ローカルPC）

### 起動方法

`Qwen_develop` フォルダにある **`download_tool.bat`** をダブルクリック

または VSCode ターミナルで：

```powershell
python download_tool.py
```

### 操作

1. ウィンドウが開く
2. YouTube URL を貼り付ける（例: `https://youtu.be/XXXXXXX`）
3. **Enter キー** または「ダウンロード」ボタンを押す
4. ✅ が出たら `output/` フォルダが自動で開く
5. 保存された `.wav` ファイルを確認する

> **ポイント**: 動画が何分あっても **最初の10秒だけ**自動で切り取って保存する。

---

## STEP 2｜Colab でノートブックを起動する

### URL
```
https://colab.research.google.com/github/yuto-f04/Qwen_develop/blob/main/colab_runner.ipynb
```

### 手順

1. 上のURLをブラウザで開く
2. **ランタイム → ランタイムのタイプを変更 → T4 GPU** を選択
3. **「すべてのセルを実行」** を押す（または Cell 1 → 2 → 3 を順番に ▶）

| セル | 内容 | 所要時間 |
|------|------|----------|
| Cell 1 | リポジトリの取得（clone/pull） | 約30秒 |
| Cell 2 | パッケージのインストール | 約3分 |
| Cell 3 | Gradio アプリ起動 | 約30秒 |

4. Cell 3 の出力に出る **`Running on public URL: https://xxxxx.gradio.live`** をクリック

---

## STEP 3｜Gradio UI で音声を生成する

### Step 1（クリーン音声を作る）

1. 「音声ファイルをアップロード」に STEP 1 で保存した `.wav` をドラッグ＆ドロップ
2. **「① クリーン音声を生成（BGM除去 → 10秒）」** を押す
3. ✅ が出るまで待つ（Demucsで BGM・ノイズ除去）

### Step 2（文字起こし）

1. **「② 文字起こし実行」** を押す
2. Whisper が音声をテキストに変換する
3. 間違いがあれば手で修正する（そのままでも可）

### Step 3（台本から音声生成）

1. 台本テキストを「台本テキスト」欄に貼り付ける
2. **「③ 音声生成開始」** を押す
3. 完成音声プレイヤーが表示されたらダウンロードする

> **完成ファイル名**: `tour_guide.wav`

---

## よくあるエラーと対処法

| 症状 | 原因 | 対処 |
|------|------|------|
| `ffprobe and ffmpeg not found` | ffmpegがPATHに未登録 | `download_tool.bat` を使えば自動解決 |
| Colab で YouTube DL が失敗 | bot 対策 | ローカルでDLして手動アップロード（このガイドの手順通り） |
| CUDA out of memory | 参照音声が長すぎる | STEP 1 で10秒以下に切り取られているはず。再確認 |
| 台本から文が抽出できない | 句点がない | 台本に `。` `！` `？` を入れる |
| 途中でコケた | TTS生成中断 | Gradio の「途中から再開する」チェックを入れて再実行 |

---

## ファイルの場所

| ファイル | 場所 |
|----------|------|
| ダウンロードした参照音声 | `Qwen_develop/output/*.wav` |
| 完成音声 | `Qwen_develop/output/tour_guide.wav` |
| 各文の音声（中間ファイル） | `Qwen_develop/output/sentences/` |
| 台本テキスト（自動保存） | `Qwen_develop/output/ui_state.json` |

---

## パラメータを変えたいとき

`src/config.py` を編集する。

```python
MAX_REF_SECONDS = 10      # 参照音声の長さ（秒）
SILENCE_MS = 400          # 句点後の無音（ミリ秒）
SILENCE_COMMA_MS = 150    # 読点後の無音（ミリ秒）
WHISPER_MODEL_SIZE = "base"  # 文字起こし精度（base/small/medium）
```

編集後は GitHub に push → Colab で Cell 1 を再実行（git pull）すれば反映される。

---

## GitHub への push 手順

```powershell
# VSCode ターミナルで
git add .
git commit -m "feat: 変更内容のメモ"
git push
```

push 後、Colab の Cell 1 を再実行すれば最新コードが反映される。
