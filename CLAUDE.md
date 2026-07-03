# CLAUDE.md — 開発ルール

## プロジェクト概要

立命館大学キャンパスを巡る「嘘ツアーガイド」音声を生成する卒業研究プロジェクト。
Qwen3-TTS のゼロショット音声クローン（ref_audio + ref_text）を使い、
参照音声の話者の声で台本を読み上げる音声を自動生成する。

## 開発環境の役割分担

| 環境 | 役割 |
|------|------|
| **ローカル (ここ)** | コードの実装・テスト・デバッグ。GPU 不要。Claude Code がここで完結する。 |
| **Google Colab** | GPU 依存処理（TTS 推論・Demucs・Whisper）の実行専用。コードは書かない。 |

**開発サイクル:**
1. ここで TDD で実装
2. GitHub に push
3. Colab で `git pull` して実行
4. エラーが出たらエラー文をここに貼り付けて解決
5. 1 に戻る

## 必須ルール

### テスト方針

- 開発は必ず **TDD (Red → Green → Refactor)** で進める。**実装より先にテストを書く。**
- コミット前に必ず `pytest tests/` を実行して全テストが通ることを確認する。

**CPU 専用コード** — ローカルで完全テストする:
- `src/script_splitter.py` の `split_into_sentences`
- `src/audio_merge.py` の `merge_audio_files`
- `src/audio_preprocess.py` の `trim_reference_audio`

**GPU 依存コード** — `unittest.mock` でモデル/subprocess 呼び出しをモック化し、
入出力の形式のみをローカルでテストする。実際の動作確認は Colab で行う:
- `src/audio_preprocess.py` の `download_audio`, `remove_bgm`, `transcribe`
- `src/tts_generate.py` の `generate_sentence_audio`, `generate_all`

### コーディングルール

- **パラメータはハードコードしない。** 無音長さ・参照音声秒数・出力先ディレクトリ等は
  必ず `src/config.py` に集約する。
- **GPU 依存の import は関数の内側に書く。** `import torch`、`from qwen_tts import ...`、
  `import whisper` 等はすべて関数内でのみ import する。
  これによりローカルでモジュールをインポートしてもエラーにならない。
- `app.py` は Colab 上で GPU を使って起動する前提。
  ローカルでは `import app` が通ることだけ確認できればよい。

### ドキュメントルール

- **タスク開始前に `docs/ERRORS.md` と `docs/PROGRESS.md` を必ず読み込む。**
- エラーが出て解決したら、必ず `docs/ERRORS.md` に以下の形式で追記する:
  ```
  ## [日付] エラータイトル
  - **発生状況**: どこで何をしていたか
  - **エラーメッセージ**: 実際のエラー文
  - **原因**: なぜ起きたか
  - **解決策**: どう直したか
  - **再発防止**: 今後どうするか
  ```
- Colab 側で発生したエラーはユーザーがテキストをここに貼り付けるので、
  解決して `docs/ERRORS.md` に記録する。

### Git ルール

- コミットメッセージは以下のプレフィックスを使う:
  - `feat:` 新機能
  - `fix:` バグ修正
  - `test:` テスト追加・修正
  - `docs:` ドキュメント更新
- コミット前に `pytest tests/` が全部通ることを確認する。

## ディレクトリ構成

```
Qwen_develop/
├── CLAUDE.md              # このファイル（開発ルール）
├── app.py                 # Gradio UI（Colab 上で起動）
├── conftest.py            # pytest が src を認識するための空ファイル
├── requirements.txt       # 依存パッケージ
├── .gitignore
├── docs/
│   ├── PROGRESS.md        # 進捗管理（フェーズ・チェックボックス）
│   └── ERRORS.md          # エラー記録（発生→解決の都度追記）
├── src/
│   ├── __init__.py
│   ├── config.py          # パラメータ集約（ここだけ変更すれば全体に反映）
│   ├── audio_preprocess.py  # BGM除去・文字起こし・トリミング
│   ├── script_splitter.py   # 台本を句点で1文ずつ分割
│   ├── tts_generate.py      # Qwen3-TTS 推論（GPU依存）
│   └── audio_merge.py       # 音声ファイル結合
└── tests/
    ├── __init__.py
    ├── test_script_splitter.py
    ├── test_audio_preprocess.py
    ├── test_tts_generate.py
    ├── test_audio_merge.py
    └── test_app.py
```
