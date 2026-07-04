# PROGRESS.md — 開発進捗

## 研究背景

立命館大学の施設を巡る「嘘ツアーガイド」音声を自動生成する卒業研究。
実際には存在しない「裏の目的」や「秘密の機能」を語るガイド台本を、
Qwen3-TTS のゼロショット音声クローンで特定の話者の声に変換する。

## 開発環境の役割分担

| 環境 | 役割 |
|------|------|
| **ローカル (VS Code + Claude Code)** | コードの実装・TDD・デバッグ |
| **Google Colab (GPU)** | TTS 推論・Demucs・Whisper の実行 |

## パイプライン全体像

```
[YouTube URL]          [台本テキスト]
     |                       |
     v                       v
 yt-dlp                 script_splitter
     |                   (句点で1文ずつ分割)
     v                       |
  Demucs                     |
 (BGM除去)                   |
     |                       |
     v                       |
  Whisper                    |
 (文字起こし)                 |
     |                       |
     v                       v
 trim_reference_audio ──> Qwen3-TTS
 (10秒にカット)          (1文=1ファイル)
                              |
                              v
                         audio_merge
                        (0.4秒の無音を挟んで結合)
                              |
                              v
                         完成音声 (tour_guide.wav)
```

## 開発フェーズ

### Phase 1: リポジトリ再構築
- [x] ディレクトリ構成を整備 (`src/`, `tests/`, `docs/`)
- [x] Qwen_develop.ipynb の内容を各モジュールに移植
- [x] `src/config.py` でパラメータ集約
- [x] `src/script_splitter.py` 実装
- [x] `src/audio_preprocess.py` 実装
- [x] `src/tts_generate.py` 実装
- [x] `src/audio_merge.py` 実装
- [x] `app.py` (Gradio UI) 実装
- [x] `CLAUDE.md` 作成
- [x] `docs/PROGRESS.md` 作成
- [x] `docs/ERRORS.md` 作成
- [x] `colab_runner.ipynb` 作成
- [x] `requirements.txt` 作成
- [x] `.gitignore` 作成
- [x] `pytest tests/` 全通過確認

### Phase 2: CPU 側 TDD 実装
- [x] `test_script_splitter.py` 作成・全通過
- [x] `test_audio_merge.py` 作成・全通過
- [x] `test_audio_preprocess.py` の `trim_reference_audio` テスト作成・全通過
- [x] `test_app.py` (インポート確認) 作成・全通過

### Phase 3: GPU 側モック実装
- [x] `test_audio_preprocess.py` の mock テスト (download_audio, remove_bgm, transcribe)
- [x] `test_tts_generate.py` の mock テスト (generate_sentence_audio, generate_all)

### Phase 3.5: 読み正規化 (汎用ルールベース)
- [x] `src/text_normalizer.py` 実装 — 2階層構造(例外辞書 + パターンルール)
- [x] `tests/test_text_normalizer.py` 全49テスト通過
- [x] `app.py` Step3 に `normalize_for_tts()` を統合(ユーザー操作変更なし)

**対応ルール一覧 (優先度順):**

| ルール | 対象 | 例 |
|--------|------|----|
| 1. 例外辞書 | 固有名詞・登録語 | BARCO→バルコ, Dolby Atmos→ドルビー アトモス |
| 2. コード表記 | 英字+数字、英字+棟/館、数字+F | H121→エイチひゃくにじゅういち、4F→よんかい、H棟→エイチとう |
| 3. 時刻 | HH:MM | 12:40→じゅうにじよんじゅっぷん |
| 4. 年号 | YYYY年 | 2025年→にせんにじゅうごねん |
| 5. 数字+単位 | m/cm/km/kg/席/階/分/秒/本/枚/個 | 200席→にひゃくせき |
| 6. フォールバック | 辞書・コード以外の2文字以上英字 | XYZ→エックスワイゼット |

**例外辞書への追記方法:**
```python
from src.text_normalizer import add_reading_override
add_reading_override("新しい略語", "よみがな")
```
新しい台本で自動判定が難しい固有名詞が出てきたら、ここに追記する運用とする。

### Phase 4: Gradio UI 統合
- [ ] app.py の UI 動作確認 (Colab 上で share=True で起動)
- [ ] YouTube URL 入力 → 音声取得フロー確認
- [ ] 参照音声ファイルアップロード → TTS 生成フロー確認
- [ ] 進捗バー・エラーメッセージの表示確認

### Phase 5: Colab 実機テスト
- [ ] Demucs による BGM 除去動作確認
- [ ] Whisper による文字起こし動作確認
- [ ] Qwen3-TTS による音声クローン生成動作確認
- [ ] パイプライン全体 (YouTube → 完成音声) 動作確認
- [ ] 生成音声のクオリティ確認・パラメータ調整

## 既知の課題

| 課題 | 詳細 | 対応方針 |
|------|------|----------|
| 参照音声の長さ | 長すぎると CUDA OOM。10秒程度が安定 | `MAX_REF_SECONDS = 10` |
| イントネーションの上ずり | 句読点前後で音が上ずることがある | 文分割の単位を調整して対応 |
| 海外なまり | 日本語でも英語っぽいなまりが出やすい | `ref_text` の精度向上で改善見込み |
| 文分割の粒度 | 読点(、)でも分割する設計に変更済み。読点後は 150ms、句点後は 400ms の無音 | 解決済み |

## 更新ログ

| 日付 | 内容 |
|------|------|
| 2026-07-03 | Phase 1 完了: リポジトリ再構築。ディレクトリ構成整備、全モジュール実装、全テスト通過確認 |
| 2026-07-03 | Phase 2・Phase 3 完了: CPU・GPU モック側のテストを同時実装・全通過 |
| 2026-07-03 | Phase 3.5 完了: 読み正規化モジュール実装。汎用2階層設計(例外辞書+パターン6種)、全86テスト通過 |
