# STATUS.md — システム現在地スナップショット

> **作業開始前に必ず確認。実装・テスト・Colab確認が完了したら即更新してコミットする。**

---

## 最終更新

| 項目 | 内容 |
|------|------|
| 更新日 | 2026-11-03 |
| ローカルテスト | 197件 全通過 |
| 直近の作業 | Phase 6 完了: 事後アンケート分析プログラム追加 |

---

## 凡例

| 記号 | 意味 |
|------|------|
| ✅ | 確認済み・正常動作 |
| ✅(mock) | ローカルでモックテスト通過（実GPU動作は Colab で確認） |
| ⚠️ | 部分確認・条件付きで動作 |
| ❌ | 壊れている・未解決の問題あり |
| ❓ | 未確認（Colab での実行テストがまだ） |

---

## src/ ファイル状態

| ファイル | 主な関数・役割 | ローカルテスト | Colab確認 | 備考 |
|---------|--------------|--------------|---------|------|
| `config.py` | 全パラメータ集約（定数のみ） | ✅ | ✅ | 分析セクション追加済み |
| `script_splitter.py` | `split_into_sentences` — 句点で1文ずつ分割 | ✅ | ✅ | 句点(。！？)のみ分割。読点は分割しない |
| `audio_preprocess.py` | `download_audio`, `remove_bgm`, `transcribe`, `trim_reference_audio` | ✅(mock) | ⚠️ | yt-dlp は cookies.txt + `player_client=tv,web` が必要 |
| `tts_generate.py` | `generate_sentence_audio`, `generate_all` | ✅(mock) | ⚠️ | sox の apt-get インストールが必要 |
| `audio_merge.py` | `merge_audio_files` — 無音を挟んで結合 | ✅ | ✅ | 無音 400ms (SILENCE_DURATION) |
| `text_normalizer.py` | `normalize_for_tts` — 読み正規化（2階層: 辞書+パターン） | ✅ | ❓ | Colab での実機読み上げ確認はまだ |
| `analysis/load.py` | `load_and_clean`, ペア突き合わせ・グループ判定 | ✅ | ❓ | ローカル分析ツール。Colab不要 |
| `analysis/scoring.py` | `compute_score`, Cronbach's α | ✅ | ❓ | ローカル分析ツール。Colab不要 |
| `analysis/stats_tests.py` | ウィルコクソン・マン・ホイットニー・Cliff's δ | ✅ | ❓ | ローカル分析ツール。Colab不要 |
| `analysis/figures.py` | 対応図・箱ひげ図・棒グラフ・積み上げグラフ | ✅ | ❓ | ローカル分析ツール。Colab不要 |
| `analysis/report.py` | `run_full_analysis` — レポート生成・CSV書き出し | ✅ | ❓ | ローカル分析ツール。Colab不要 |
| `app.py` | Gradio UI（Colab 上で起動） | ✅(import) | ⚠️ | UI 操作フロー全体の確認が残っている |

---

## テスト状態

| テストファイル | テスト件数 | 状態 | 最終確認日 |
|--------------|---------|------|-----------|
| `test_script_splitter.py` | — | ✅ | 2026-11-03 |
| `test_audio_preprocess.py` | — | ✅ | 2026-11-03 |
| `test_tts_generate.py` | — | ✅ | 2026-11-03 |
| `test_audio_merge.py` | — | ✅ | 2026-11-03 |
| `test_text_normalizer.py` | 49件 | ✅ | 2026-11-03 |
| `test_app.py` | — | ✅ | 2026-11-03 |
| `test_analysis_load.py` | — | ✅ | 2026-11-03 |
| `test_analysis_scoring.py` | — | ✅ | 2026-11-03 |
| `test_analysis_stats.py` | — | ✅ | 2026-11-03 |
| `test_analysis_report.py` | — | ✅ | 2026-11-03 |
| **合計** | **197件** | **✅ 全通過** | 2026-11-03 |

---

## Colab 確認済み動作

| 機能 | 状態 | 確認時期 | 備考 |
|------|------|---------|------|
| Demucs BGM除去 | ⚠️ 部分確認 | 2026-10 | sox インストール必須 |
| Whisper 文字起こし | ⚠️ 部分確認 | 2026-10 | large-v3 対応済み |
| Qwen3-TTS 音声生成 | ⚠️ 部分確認 | 2026-10 | `Setting pad_token_id` 警告は抑制済み |
| yt-dlp ダウンロード | ⚠️ 条件付き | 2026-07 | cookies.txt + `player_client=tv,web` 必須 |
| パイプライン全体 | ❓ 未確認 | — | YouTube→完成音声の全体フローはまだ |

---

## 既知の未解決課題

| 課題 | 影響 | 対応方針 |
|------|------|---------|
| イントネーションの上ずり | 音質 | 文分割単位の調整で軽減見込み |
| 海外なまり | 音質 | `ref_text` 精度向上で改善見込み |
| app.py の UI 操作フロー未確認 | Phase 4 未完 | Colab で `share=True` 起動して確認 |
| パイプライン全体テスト未実施 | Phase 5 未完 | Colab で YouTube→完成音声の全体フロー確認 |

---

## 更新ルール

1. **`pytest tests/` を実行し件数が変わったら「テスト状態」テーブルを更新する**
2. **Colab で新しい機能の動作確認ができたら ❓ → ✅ or ⚠️ に変える**
3. **新しいファイルを追加したら「src/ ファイル状態」に行を追加する**
4. **更新したら「最終更新」の日付と「直近の作業」も書き換える**
5. **`docs:` プレフィックスのコミットに含めてpushする**
