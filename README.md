# Qwen_develop
卒業研究 — 立命館大学キャンパス「嘘ツアーガイド」音声生成

---

## 音声生成（Colab）

Colab 上で `colab_runner.ipynb` を実行してください。詳細は `docs/PROGRESS.md` を参照。

---

## 事後アンケート分析

### 1. 回答CSVのダウンロード方法

1. Google フォームを開き、「回答」タブをクリック
2. 右上の「⋮」→「回答をダウンロード（.csv）」を選択
3. ダウンロードした CSV を `data/responses.csv` として保存

### 2. 依存パッケージのインストール

```powershell
pip install -r requirements-analysis.txt
```

### 3. 実行コマンド

```powershell
# CSV が data/responses.csv にある場合（引数省略可）
python run_analysis.py

# パスを明示する場合
python run_analysis.py --input data/responses.csv --outdir output/analysis

# 氏名エイリアスファイル（任意）を使う場合
python run_analysis.py --aliases data/name_aliases.csv
```

実行が完了すると、ターミナルに主指標の結果が4〜5行で表示されます。

### 4. 出力の見方

| ファイル | 内容 |
|---------|------|
| `output/analysis/report.md` | 日本語レポート（全分析結果・注意書き） |
| `output/analysis/tidy.csv` | 整形済み縦長データ（1回答1行） |
| `output/analysis/wide.csv` | 1人1行の横長データ（条件A/Bを列に展開） |
| `output/analysis/free_text.csv` | 自由記述の書き出し |
| `output/analysis/coding_sheet.csv` | 違和感の分類作業用シート |
| `output/analysis/lie_list.csv` | 嘘11か所のID・場所・内容 |
| `output/analysis/figures/` | 図（PNG）3枚以上 |

### 5. 自由記述の分類（研究者が手動で行う）

1. `output/analysis/coding_sheet.csv` を開く
2. 「該当する嘘ID」列に嘘IDを記入（例: `H1`, `K3` など）
3. 「本当の部分への違和感か」「メモ」を適宜記入
4. 完成したファイルを `data/coding_done.csv` として保存
5. `python run_analysis.py` を再実行すると嘘IDごとの気づき集計が追加される

### 6. ダミーデータでの動作確認

```powershell
python scripts/make_dummy_data.py
python run_analysis.py
```

架空の20人×2回答のデータで分析が最後まで動くことを確認できます。

### 7. 氏名の表記ゆれ対応

`data/name_aliases.csv`（列: `alias,name`）を作成すると自動的に適用されます。
例：

```csv
alias,name
田中　太郎,田中太郎
鈴木 花子,鈴木花子
```

---

## ディレクトリ構成

```
Qwen_develop/
├── run_analysis.py          # 分析エントリポイント
├── scripts/
│   └── make_dummy_data.py   # ダミーデータ生成
├── src/
│   ├── config.py            # 全パラメータ（音声生成・分析）
│   └── analysis/
│       ├── load.py          # データ読み込み・前処理
│       ├── scoring.py       # エンタメ体験得点・Cronbach's α
│       ├── stats_tests.py   # 検定・効果量・信頼区間
│       ├── figures.py       # 図の生成
│       └── report.py        # 分析実行・レポート生成
├── tests/
│   ├── test_analysis_load.py
│   ├── test_analysis_scoring.py
│   ├── test_analysis_stats.py
│   └── test_analysis_report.py
├── data/                    # 実験データ（.gitignore 対象）
│   └── responses.csv        # Googleフォームから取得したCSV
└── output/analysis/         # 分析出力（.gitignore 対象）
```
