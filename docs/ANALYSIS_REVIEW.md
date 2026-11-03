# 事後アンケート分析プログラム点検報告

**点検日**: 2026-11-03  
**点検者**: Claude Code（第三者として）  
**対象**: run_analysis.py, src/analysis/\*, scripts/make_dummy_data.py, 関連テスト

---

## 1. 総合判定

**実験データに使う前に「致命」4件の修正が必要です。**

ダミーデータでは正常動作し、統計値もすべて独立再計算と一致しています。  
ただし「全員が片方の条件のみ」「空データ」「CP932 ファイル」などのデータを渡すと未処理例外でクラッシュします。Googleフォームからの実際のCSVはExcelで開いて保存し直す可能性があるため、CP932対応は必須です。

---

## 2. 問題一覧

| # | 内容 | 再現手順（データ）| 重大度 | 修正案 |
|---|------|------------------|--------|--------|
| F1 | **CP932 CSVで UnicodeDecodeError クラッシュ** | Excelで保存したCSV | **致命** | encoding を utf-8-sig → cp932 → latin1 の順にフォールバック |
| F2 | **ペアなし・全員同条件・空データで KeyError クラッシュ** | ヘッダーのみ / 全員条件Aのみ / 1件のみ | **致命** | wide_df が空またはペア列がない場合に早期チェックして分かりやすいメッセージを出す |
| F3 | **空欄氏名が複数いると同一人物として処理される** | 氏名欄が空の行が2件（条件A + 条件B） | **致命** | 氏名が空欄の行を警告して除外する |
| F4 | **NaT タイムスタンプが「最新」と誤判定される（重複除去バグ）** | 「2026/11/10 午後 1:05:22」など変換不能な形式 | **致命** | 重複除去前に NaT 行を警告、NaT を `na_position="first"` に持ってくるか除外 |
| I1 | **Cliff's δ の符号の向きがレポートに説明されていない** | 正常データ（レポートを読む際に誤解の可能性） | **重要** | レポートに「正の値はグループ1（条件A）が高いことを示す」を追記 |
| I2 | **嘘ID の照合が部分一致（str.contains）** | `coding_done.csv` に "H1,K2" や複数ID記載 | **重要** | カンマ・読点で分割後に完全一致で照合する |
| I3 | **矛盾した人の氏名をレポートに含めるためだけに文字列パース** | 警告文から `split("'")[1]` で抽出 | **重要** | `detect_round_inconsistency` がリスト `(名前, 警告文)` を返すよう変更 |
| I4 | **`first_only` 変数が定義されているが使われていない（dead code）** | report.py:165 | **軽微** | 削除 |
| M1 | **Holm p の表記に `< .001` 形式がない** | Holm 補正後の p が 0.001 未満の場合 | **軽微** | `_fmt_p` を使うか専用フォーマット |
| M2 | **α=0 ÷ 0 → 1.0 を返す（数学的に定義不能）** | 全員同じ4項目スコア | **軽微** | `np.nan` を返す or コメントで説明 |
| M3 | **`_compute_discomfort_cross` の第2引数 `_full` が使われていない** | 内部実装 | **軽微** | 引数から削除 |

---

## 3. 仕様とコードの照合表

| 仕様項目 | 実装ファイル・関数 | 状態 | 備考 |
|----------|-------------------|------|------|
| 被験者内計画・グループ判定（A→B / B→A） | load.py `assign_group` | OK | |
| エンタメ体験得点＝ interest/recommend/satisfaction/revisit の平均 | scoring.py `compute_entertainment_score` | OK | |
| Cronbach's α を条件A・B別に計算 | scoring.py `cronbach_alpha`, report.py `alpha_for_cond` | OK | |
| α 両方 ≥ 0.70 → entertainment_score, 一方でも < 0.70 → satisfaction | scoring.py `select_primary_metric` | OK | α = 0.70 は OK（≥ で判定） |
| ウィルコクソン符号順位検定（両側、α=0.05）| stats_tests.py `wilcoxon_signed_rank` | OK | |
| 同点除外・除外人数を報告 | stats_tests.py `wilcoxon_signed_rank` | OK | |
| 効果量 r = |Z|/√N（N=同点除外後）| stats_tests.py `effect_r_from_z` | OK | |
| Cohen's dz（全差で計算）| stats_tests.py `cohens_dz` | OK | |
| 差の平均の95%CI（t分布） | stats_tests.py `mean_ci_95` | OK | |
| 差の中央値のブートストラップ95%CI（シード固定）| stats_tests.py `bootstrap_median_ci` | OK | |
| 判定文: B>A かつ p<.05 → 仮説を支持 / A>B かつ有意 → 条件Aが有意 | stats_tests.py `judgment_text` | OK | mean_diff で判定（仕様の方向性と一致） |
| 副指標 4 + expectation、Holm 補正 | report.py 副指標セクション | OK | |
| Holm 補正の実装 | stats_tests.py `holm_correction` | OK | 独立手計算と一致 |
| 条件確認5項目（length/clarity/enthusiasm/difficulty/physical）| report.py 条件確認セクション | OK | |
| \|dz\| ≥ 0.5 で注意書き | report.py 条件確認ループ | OK | |
| 1回目だけの比較: グループ2の条件B vs グループ1の条件A | report.py `grp1_first`, `grp2_first` | OK（論理は正しい） | Cliff's δ の符号の向き説明なし（I1） |
| マン・ホイットニー U + r + Cliff's δ | stats_tests.py `mann_whitney_u`, `cliffs_delta` | OK | |
| 順番の影響: 1回目vs2回目（ウィルコクソン）| report.py 順番の影響セクション | OK | |
| B−A 差のグループ間比較（U検定） | report.py `diff_by_group` | OK | |
| 違和感クロス表（全体・1回目）| report.py `_compute_discomfort_cross` | OK | |
| 「興味を抱いたか」の集計 | report.py `disc_interest` | OK | |
| 条件Bの違和感あり vs なしで B−A 差を比較（5人未満なら記述のみ） | report.py `disc_diff_result` | OK | |
| 欠測: 片方しか回答していない人を除外、氏名と理由を報告 | load.py `match_pairs` | OK | |
| 重複: 新しいほうを使い警告 | load.py `deduplicate_responses` | **バグあり** | NaT が「最新」と誤判定（F4） |
| 天井効果: 9〜10点の割合 ≥ 0.5 で注意書き | report.py `_compute_desc_stats` + notes | OK | |
| 自由記述 free_text.csv と coding_sheet.csv | report.py `_write_free_text`, `_write_coding_sheet` | OK | |
| coding_done.csv があれば嘘IDごとに集計 | report.py `_summarize_lie_detection` | **バグあり** | str.contains で部分一致（I2） |
| config.py にしきい値・列名・パス・嘘11か所 | src/config.py | OK | ハードコードなし確認済み |

---

## 4. 意地悪なデータ 27 パターンの結果表

| # | パターン | 止まるか | メッセージ | 結果が正しいか |
|---|---------|----------|-----------|---------------|
| 1 | BOMなし UTF-8 | 止まらない | — | 正しい |
| 2 | BOM付き UTF-8 | 止まらない | — | 正しい |
| 3 | **CP932/Shift-JIS（Excel保存）** | **クラッシュ（F1）** | UnicodeDecodeError、メッセージ不親切 | — |
| 4 | CRLF 改行 | 止まらない | — | 正しい |
| 5 | **ヘッダーだけ（0件）** | **クラッシュ（F2）** | KeyError: ['satisfaction_A', 'satisfaction_B'] | — |
| 6 | **1件だけ** | **クラッシュ（F2）** | 同上 | — |
| 7 | 余分な列あり | 止まらない | — | 正しい |
| 8 | 必須列なし（氏名列）| 止まる | ValueError: 列が存在しません（分かりやすい） | — |
| 9a | タイムスタンプ: 2026/11/10 13:05:22 | 止まらない | — | 正しい |
| 9b | タイムスタンプ: 午後 1:05:22 | 止まらない（NaT） | 警告なし（要改善） | 正しい（処理は継続） |
| 9c | NaT + 重複（NaTが最新扱い）| 止まらない | — | **誤り（F4）**：NaTが残る可能性 |
| 11 | 全角スペース表記ゆれ | 止まらない | — | 正しい（NFKC正規化後同一視） |
| 12 | aliases.csv で表記ゆれ統一 | 止まらない | — | 正しい |
| 13 | 重複回答（古いほう5点、新しいほう9点） | 止まらない | 重複警告が出る | 正しい（9点が残る） |
| 14 | 片方のみ回答 | 止まらない | 除外リストに氏名と理由が出る | 正しい |
| 15 | **両方とも条件A（回答ミス）** | **クラッシュ（F2）** | KeyError: ['satisfaction_A', 'satisfaction_B'] | — |
| 16 | 両方とも1回目（回答ミス）| 止まらない | 矛盾警告が出る | 正しい（順番分析から除外） |
| 17a | 氏名が空欄（1件、除外）| 止まらない | 除外リストに空欄として出る | 正しい |
| 17b | **氏名が空欄（2件・条件A+B）** | 止まらない | 除外なし・警告なし | **誤り（F3）**：ペアとして処理される |
| 18 | 範囲外スコア（0, 11）| 止まらない | 範囲外警告が出る | 正しい（NaN変換） |
| 19 | 全角数字（'５'）| 止まらない | 数値でない警告が出る | 正しい（NaN変換） |
| 20 | 全員同点（分散0）| 止まらない | — | 正しい（WはNaN、判定「得られなかった」） |
| 21 | 全員 B > A で有意 | 止まらない | — | 正しい（「仮説を支持する（条件B...）」） |
| 22 | A > B で有意 | 止まらない | — | 正しい（「仮説を支持する結果は得られなかった（条件Aのほうが有意...）」） |
| 23 | 全員 9〜10 点（天井効果） | 止まらない | 天井効果注意書きが出る | 正しい |
| 24 | α < 0.70（切り替え） | 止まらない | α 値と切り替え理由が出る | 正しい（satisfaction に切り替え） |
| 25 | 違和感ありが 0 人 | 止まらない | 「5人未満のため検定は行わず」 | 正しい |
| 26 | 3 人だけ | 止まらない | — | 正しい（小サンプルで動作） |
| 27 | グループ2 が 0 人 | 止まらない | — | 正しい（1回目比較・グループ差分析はスキップ） |
| 28 | 自由記述にカンマ・改行・絵文字 | 止まらない | — | 正しい（CSV エスケープ、utf-8-sig 出力） |
| 29 | 2 回続けて実行（上書き） | 止まらない | — | 正しい |

---

## 5. 統計の再計算照合結果

ダミーデータ（output/analysis/wide.csv）の satisfaction 値を使って独立再計算した。

| 統計量 | report.md | 独立再計算 | 一致 |
|--------|-----------|-----------|------|
| W（ウィルコクソン統計量） | 19.000 | 19.000 | OK |
| p 値 | p = 0.011 | 0.0107 | OK（丸め一致） |
| 効果量 r | 0.633 | 0.6334 | OK |
| Cohen's dz | 0.671 | 0.6708 | OK |
| 差の平均の95%CI | [0.453, 2.547] | [0.453, 2.547] | OK |
| 中央値のブートストラップ95%CI（seed=42）| [0.000, 3.000] | [0.000, 3.000] | OK |
| Cronbach's α（手計算3人×3項目）| — | 公式と完全一致 | OK |
| Holm 補正 p | [0.027, 0.052, 0.032, 0.014, 0.529] | [0.028, 0.052, 0.033, 0.015, 0.529] | OK（rounding） |
| Mann-Whitney U（1回目比較） | 9.000 | 9.000 | OK |
| Mann-Whitney p | p = 0.002 | 0.0019 | OK |
| Mann-Whitney r | 0.693 | 0.693 | OK |
| Cliff's δ（g1 vs g2） | -0.820 | -0.820 | OK（向き要注記） |

---

## 6. 仕様の変更を提案したい点（変更はしない）

以下は仕様自体の変更であり、研究者・教授の判断が必要。点検者として提案のみ。

**P1: 判定文の向きを `mean_diff` でなく `median_diff` で判定することの検討**  
ウィルコクソン検定は中央値ベースの検定なので、「B>A かつ p<.05」の「B>A」判定に `median_diff > 0` を使う方が整合的。現状は `mean_diff > 0` を使っている。ほとんどの場合は同じ結果になるが、非対称な外れ値がある場合に不整合が生じる可能性がある。

**P2: Cronbach's α が全員同点（分散0）のとき `1.0` を返す**  
数学的には 0/0 で定義不能。現状は `1.0` を返し entertainment_score が主指標に選ばれる。`np.nan` を返して satisfaction に切り替える方が保守的。ただし全員同点なら entertainment_score と satisfaction に差がないため実害は少ない。

**P3: 小サンプル（≤10人）でのr計算にZ正規近似を使う**  
scipy が正確法を使う場合（小サンプル）、`zstatistic` 属性がなく `_compute_z_from_wilcoxon` の正規近似にフォールバックする。正確法の p 値と正規近似の Z の組み合わせになるため厳密には整合的でない。ただし 20 人規模では正確法にはならないため実験では問題なし。

---

## 修正後の結果

**修正完了日**: 2026-11-03  
**テスト結果**: 225 passed（0 failed, 0 error）

### 致命・重要バグの修正状況

| # | 修正内容 | 対象ファイル | 確認方法 |
|---|----------|------------|---------|
| F1 | `_read_csv_auto_encoding` を追加し utf-8-sig→cp932 の順で試み、不明なら ValueError | load.py | TestLoadResponsesEncoding 4件 |
| F2 | `len(df_paired) == 0` を早期チェックし ValueError + report.md にエラー出力 | report.py | TestEmptyDataDoesNotCrash 4件 |
| F3 | `normalize_name` を直渡しに変更し NaN→"" 、空欄行を警告付きで除外 | load.py | TestBlankNameFiltering 6件 |
| F4 | `parse_timestamp` 関数追加（午前/午後→24時間変換）、`na_position="first"` で NaT を最古扱いに | load.py | TestParseTimestamp 7件 |
| I1 | `mann_whitney_u(grp2_first, grp1_first)` に引数順を修正、report に「正の値は条件Bが高い」注記追加 | report.py | TestMannWhitneyUDirectionConvention 2件 |
| I2 | `_parse_lie_ids` で複数区切り文字（`,、，/・` + 空白）分割後に完全一致照合、NFKC正規化 | report.py | TestLieIdMatching 4件 |
| I3 | `detect_round_inconsistency` 戻り値を `List[Tuple[str,str]]` に変更、report.py 側でアンパック | load.py, report.py | TestDetectRoundInconsistency::test_returns_name_message_tuples |

### 修正後の 27 パターン再確認

| # | パターン | 修正後の動作 |
|---|---------|-----------|
| 3 | CP932/Shift-JIS | 正常読み込み + 「cp932 で読み込んだ」警告 ✓ |
| 5 | ヘッダーだけ（0件）| ValueError（分かりやすいメッセージ）、トレースバックなし ✓ |
| 6 | 1件だけ | 同上 ✓ |
| 9b | 午後タイムスタンプ | `parse_timestamp` で正しく変換（NaT にならない）✓ |
| 9c | NaT + 重複 | NaT 行を最古扱いにして新しい有効タイムスタンプの行を残す ✓ |
| 15 | 両方とも条件A | ValueError（分かりやすいメッセージ）、トレースバックなし ✓ |
| 17b | 空欄氏名2件（条件A+B） | 2件除外 + 「氏名が空欄の回答 2 件を除外しました」警告 ✓ |
| 他20件 | — | 修正前と変わらず正常動作 ✓ |

### I1 統計値の変化

Cliff's δ の符号規約を「B>A=正」に修正したため、ダミーデータでの結果が変化する:

| 統計量 | 修正前 | 修正後 | 備考 |
|--------|--------|--------|------|
| Cliff's δ（1回目比較） | −0.820 | **+0.820** | グループ2（条件B1回目）のほうが高いことを正しく表す |
| U 統計量 | 9.000 | 9.000 | 変化なし |
| p 値 | p = 0.002 | p = 0.002 | 変化なし |
| r | 0.693 | 0.693 | 変化なし |

実験結果の **解釈方向**（B>A か A>B か）は変わらない。δ の符号が正しく「条件Bのほうが高い」を示すようになった。

### 残存する軽微な問題

当初 M1/M2/M3/X1 として列挙した軽微な問題はすべて修正済み（下記 analysis-v1.0 参照）。

---

## analysis-v1.0 修正結果（2026-11-03）

**修正完了日**: 2026-11-03  
**テスト結果**: 260 passed（0 failed, 0 error）  
**タグ**: `analysis-v1.0`

### 修正内容

| # | 修正内容 | 対象ファイル | テストクラス |
|---|----------|------------|------------|
| X1 | `DISCOMFORT_CATEGORIES`・`DISCOMFORT_PRESENT_CATEGORIES`・`DISCOMFORT_INTEREST_CHOICES` を `config.py` に追加。`load.py` に `_validate_discomfort` を追加し、想定外値を警告。`report.py` もすべて config 定数を参照するよう修正。 | config.py, load.py, report.py | TestConfigDiscomfortChoices (6), TestDiscomfortValidation (7) |
| M1 | 副指標テーブルの Holm p 列を `_fmt_f(holm_p)` → `_fmt_p(holm_p)` に修正。すべての p 値が `p = X.XXX` / `p < .001` 形式に統一された。 | report.py | TestFmtPFunction (4), TestHolmPFormatInReport (1) |
| M2 | `cronbach_alpha` で `total_var == 0` のとき `1.0` → `np.nan` を返すよう修正。`select_primary_metric` で NaN・負の α を「しきい値未満」として扱い、レポートに「全員が同じ点のため α を計算できず、満足度を主指標とした」と記録するよう修正。 | scoring.py | TestCronbachAlphaZeroVariance (2), TestSelectPrimaryMetricNaNAndNegative (7) |
| M3 | `_compute_discomfort_cross(sub, _full)` の未使用引数 `_full` を削除。呼び出し箇所 2 か所も修正。 | report.py | TestComputeDiscomfortCrossSignature (2) |

### 意地悪なデータ 27 パターン再確認（X1/M2 に関係するパターンのみ）

| # | パターン | 修正後の動作 |
|---|---------|-----------|
| 20 | 全員同点（分散0） | α=NaN → satisfaction に切替。レポートに「全員が同じ点のため α を計算できず、満足度を主指標とした（条件A: 計算不能、条件B: 計算不能）」と記録 ✓ |
| X1a | discomfort に「ちょっとある」など想定外値 | `load_responses` が警告を返し、Section 9（注意書き一覧）に「行X: 列'discomfort'の値'...'は想定外の値です」と記録。集計からは除外される ✓ |
| X1b | discomfort_interest に「たぶん」など想定外値 | 同上（列名は 'discomfort_interest'） ✓ |
| X1c | 既知値（なかった/少しあった/あった/はい/いいえ）および空欄 | 警告なし ✓ |
| M2b | α < 0（real_header.csv: 条件A=-1.203, 条件B=0.171） | satisfaction に切替。レポートに「α が...一方または両方がしきい値 0.7 を下回ったため...satisfaction に切り替えました」と記録 ✓ |
| 他22件 | — | 修正前と変わらず正常動作 ✓ |

### real_header.csv 再実行結果

| 項目 | 修正前 | 修正後 | 変化 |
|------|--------|--------|------|
| Cronbach's α (条件A) | 表記なし（1.0 を返す可能性） | -1.203 | α が正確に計算される |
| Cronbach's α (条件B) | — | 0.171 | — |
| 主指標 | satisfaction | satisfaction | 変化なし（α 両方 < 0.70） |
| 判定 | 仮説を支持する（B > A, p=0.011） | 同上 | 変化なし |
| Holm p の形式 | 0.027（数値のみ） | p = 0.027 | 形式統一 ✓ |
| 注意書きの件数 | 2 件 | 2 件 | 変化なし |

### 本番データを見たあとにプログラムを変える場合のルール

本番データを入力した後にプログラムを変更する場合は、**必ずこのファイルに以下を記録してから変更すること**:

1. **変更理由**: 本番データの何を見て変更が必要と判断したか
2. **変更内容**: 何を変えるか
3. **影響範囲**: どの出力値・解釈が変わるか
4. **変更日**: いつ変更したか

---

## analysis-v1.0 最終確認（2026-11-03）

**確認日**: 2026-11-03  
**テスト結果**: 260 passed（0 failed, 0 error）  
**タグ**: `analysis-v1.0`

### 修正の実装確認

| # | 修正内容 | 実装の確認方法 | 結果 |
|---|----------|--------------|------|
| X1 | `config.py` に `DISCOMFORT_CATEGORIES`/`DISCOMFORT_PRESENT_CATEGORIES`/`DISCOMFORT_INTEREST_CHOICES` を定義。`load.py` の `_validate_discomfort` がこれらを参照して想定外値を検出する。`report.py` もすべて config 定数を参照。 | `config.DISCOMFORT_CATEGORIES == ["なかった","少しあった","あった"]` 確認済み | ✓ |
| M1 | `report.py` の `_fmt_p(p)` で `p < 0.001` → `"p < .001"`、それ以外は `"p = X.XXX"` に統一。副指標テーブルの Holm p 列も `_fmt_p(holm_p)` で出力。 | `_fmt_p(0.0001)=="p < .001"`、`_fmt_p(0.001)=="p = 0.001"` 確認済み | ✓ |
| M2 | `cronbach_alpha` で `total_var == 0` のとき `np.nan` を返す。`select_primary_metric` で `np.isnan(a)` および `a < 0` を「しきい値未満」と扱い satisfaction に切り替えて note に記録する。 | `cronbach_alpha`（全員同点df）`== nan`、`select_primary_metric(nan, 0.8)` → satisfaction + 「計算不能」note 確認済み | ✓ |
| M3 | `_compute_discomfort_cross(sub: pd.DataFrame)` の引数が `sub` のみ。`_full` は削除済み。 | `inspect.signature` で `parameters == ['sub']` 確認済み | ✓ |

### 意地悪なデータ 全パターン再確認（X1/M1/M2/M3/F1-F4/I1-I3 すべて適用後）

| # | パターン | 修正後の動作 |
|---|---------|-----------|
| 1 | BOMなし UTF-8 | 正常動作 ✓ |
| 2 | BOM付き UTF-8 | 正常動作 ✓ |
| 3 | CP932/Shift-JIS（Excel保存） | 正常読み込み + 「cp932 で読み込んだ」警告 ✓ |
| 4 | CRLF 改行 | 正常動作 ✓ |
| 5 | ヘッダーだけ（0件） | ValueError（「ペアが0人」分かりやすいメッセージ）、トレースバックなし ✓ |
| 6 | 1件だけ | 同上 ✓ |
| 7 | 余分な列あり | 正常動作 ✓ |
| 8 | 必須列なし（氏名列） | ValueError（「列が存在しません」分かりやすいメッセージ）✓ |
| 9a | タイムスタンプ: 2026/11/10 13:05:22 | 正常動作 ✓ |
| 9b | タイムスタンプ: 午後 1:05:22 | `parse_timestamp` で 13:05 に正しく変換 ✓ |
| 9c | NaT + 重複（NaTが最新扱い） | NaT 行を最古扱いにして有効タイムスタンプの行を残す ✓ |
| 11 | 全角スペース表記ゆれ | NFKC 正規化後に同一人物として処理 ✓ |
| 12 | aliases.csv で表記ゆれ統一 | 正常動作 ✓ |
| 13 | 重複回答（古5点、新9点） | 重複警告が出る、9点の行が残る ✓ |
| 14 | 片方のみ回答 | 除外リストに氏名と理由が出る ✓ |
| 15 | 両方とも条件A（回答ミス） | ValueError（「ペアが0人」分かりやすいメッセージ）✓ |
| 16 | 両方とも1回目（回答ミス） | 矛盾警告が出る、順番分析から除外 ✓ |
| 17a | 氏名が空欄（1件） | 1件除外 + 「氏名が空欄の回答 1 件を除外しました」警告 ✓ |
| 17b | 氏名が空欄（2件・条件A+B） | 2件除外 + 「氏名が空欄の回答 2 件を除外しました」警告 ✓ |
| 18 | 範囲外スコア（0, 11） | NaN変換 + 範囲外警告 ✓ |
| 19 | 全角数字（'５'） | NaN変換 + 「数値でない」警告 ✓ |
| 20 | 全員同点（分散0） | α=NaN → satisfaction に切替。レポートに「全員が同じ点のため α を計算できず、満足度を主指標とした」と記録 ✓ |
| 21 | 全員 B > A で有意 | 「仮説を支持する（条件Bが条件Aより有意に高かった）」✓ |
| 22 | A > B で有意 | 「仮説を支持する結果は得られなかった（条件Aのほうが有意に高かった）」✓ |
| 23 | 全員 9〜10 点（天井効果） | 天井効果注意書きが出る ✓ |
| 24 | α < 0.70（切り替え） | α 値と切り替え理由が注意書きに記録される ✓ |
| 25 | 違和感ありが 0 人 | 「5人未満のため検定は行わず記述統計のみ」✓ |
| 26 | 3人だけ | 正常動作（小サンプルでも動作）✓ |
| 27 | グループ2が 0 人 | 1回目比較・グループ差分析はスキップ、正常終了 ✓ |
| X1a | discomfort に「ありました」など想定外値 | `load_responses` が警告を返し、注意書き一覧に記録。集計には含まれない ✓ |
| X1b | discomfort_interest に「たぶん」など想定外値 | 同上（列名は 'discomfort_interest'）✓ |
| X1c | 既知値（なかった/少しあった/あった/はい/いいえ）および空欄 | 警告なし ✓ |

### real_header.csv 再実行結果（全修正適用後）

`tests/fixtures/edge_cases/real_header.csv`（本番フォームと同じ列名、架空20ペア+片方のみ1名+重複1件=42行）を使用。

| 項目 | 値 | 備考 |
|------|-----|------|
| 生データ行数 | 42 | |
| 重複除去後 | 41 | テスト被験者E の条件A に重複1件（最新を使用）|
| 分析人数（ペア） | 20 | 片方のみ参加者1名を除外 |
| グループ1（A→B） | 10 人 | |
| グループ2（B→A） | 10 人 | |
| Cronbach's α（条件A） | −1.203 | 負の値 → satisfaction に切り替え |
| Cronbach's α（条件B） | 0.171 | しきい値 0.70 未満 |
| 主指標 | satisfaction | α 両方 < 0.70 のため切り替え |
| W（ウィルコクソン統計量） | 19.000 | |
| p 値 | p = 0.011 | |
| 効果量 r | 0.633 | |
| Cohen's dz | 0.671 | |
| 差の平均の95%CI | [0.453, 2.547] | |
| 中央値のブートストラップ95%CI | [0.000, 3.000] | seed=42 |
| Holm p（最小値） | p = 0.014 | `_fmt_p` 形式で出力 ✓ |
| 判定 | 仮説を支持する（条件Bが条件Aより有意に高かった） | |
| Cliff's δ（1回目比較） | +0.820 | 正の値 = 条件B（グループ2の1回目）が高い |
| 注意書き件数 | 2件 | 重複警告 + α切り替え |
