import os

# ─────────────────────────────────────────────
# 音声生成設定（既存。変更禁止）
# ─────────────────────────────────────────────

# 音声結合時に挟む無音の長さ (ミリ秒)
SILENCE_MS = 400        # 句点(。！？)後

# 参照音声の最大秒数 (これを超えたらトリミング)
MAX_REF_SECONDS = 10

# Whisper モデルサイズ（large-v3 を推奨。base は日本語精度が低い）
WHISPER_MODEL_SIZE = "large-v3"

# Qwen3-TTS モデルID
TTS_MODEL_ID = "Qwen/Qwen3-TTS-12Hz-1.7B-Base"

# TTS 生成パラメータ
TTS_SEED = 42           # 再現性のために固定
TTS_TEMPERATURE = 0.7   # 公式デフォルト(0.9)より少し低めで安定

# 出力ディレクトリ
OUTPUT_DIR = "output"
SENTENCES_DIR = os.path.join(OUTPUT_DIR, "sentences")
TRIMMED_AUDIO_PATH = os.path.join(OUTPUT_DIR, "trimmed_ref.wav")
FINAL_OUTPUT_PATH = os.path.join(OUTPUT_DIR, "tour_guide.wav")

# デフォルト参照音声パス
REF_AUDIO_PATH = "clean_audio1.wav"

# UI 状態の保存先
UI_STATE_PATH = os.path.join(OUTPUT_DIR, "ui_state.json")

# ─────────────────────────────────────────────
# 事後アンケート分析設定
# ─────────────────────────────────────────────

# ── 入出力パス ──────────────────────────────
ANALYSIS_INPUT_CSV = "data/responses.csv"
ANALYSIS_OUTPUT_DIR = "output/analysis"
ANALYSIS_NAME_ALIASES_CSV = "data/name_aliases.csv"  # 任意（なくても動く）
ANALYSIS_CODING_DONE_CSV = "data/coding_done.csv"    # 任意（なくても動く）

# ── CSVの列名マッピング ────────────────────────
# キー=内部名, 値=Googleフォームの質問文
COLUMN_MAP = {
    "timestamp":          "タイムスタンプ",
    "name":               "1. 体験者の氏名",
    "condition":          "2. ツアーの条件",
    "round":              "3. 何回目の参加ですか？",
    "interest":           "4. ツアー内容に興味を持ちましたか？",
    "length":             "5. ツアーの長さは適切でしたか？",
    "clarity":            "6. ツアー中の説明は分かりやすかったですか？",
    "enthusiasm":         "7. ガイドの語りに熱意を感じましたか？",
    "recommend":          "8. このツアーを他人におすすめできますか？",
    "expectation":        "9. ツアーは期待通りでしたか？",
    "satisfaction":       "10. このツアーに満足しましたか？",
    "difficulty":         "11. ツアー内容は難しいと感じましたか？",
    "physical":           "12. 体力面で不安は感じましたか？",
    "revisit":            "13. また参加したいと感じましたか？",
    "discomfort":         "14. ツアーの説明の中に「違和感」「気になったところ」はありましたか？",
    "discomfort_where":   "14-2. どこで「違和感」を感じたか？",
    "discomfort_why":     "14-3. なぜ「違和感」を抱いたのか？",
    "discomfort_interest":"14-4. その違和感に「興味」を抱いたか？",
    "no_interest_reason": "14-4-2. 興味を抱かなかった理由について簡単に教えてください",
    "interest_reason":    "14-4-2. 興味を抱いた理由を簡単に教えてください",
    "impression":         "15. ツアーの中で最も印象に残った場面・体験を教えてください",
    "comment":            "16. ツアー全体の感想を教えてください",
}

# ── 1〜10 のスケール項目 ───────────────────────
SCALE_ITEMS = [
    "interest", "length", "clarity", "enthusiasm", "recommend",
    "expectation", "satisfaction", "difficulty", "physical", "revisit",
]

# ── 低い方が良い項目（難しさ・体力不安）────────
REVERSE_ITEMS = ["difficulty", "physical"]

# ── エンタメ体験得点を構成する4項目 ─────────────
ENTERTAINMENT_ITEMS = ["interest", "recommend", "satisfaction", "revisit"]

# ── 副指標項目 ───────────────────────────────
SECONDARY_ITEMS = ["interest", "recommend", "satisfaction", "revisit", "expectation"]

# ── 条件確認項目 ─────────────────────────────
CONDITION_CHECK_ITEMS = ["length", "clarity", "enthusiasm", "difficulty", "physical"]

# ── 統計の閾値 ───────────────────────────────
CRONBACH_ALPHA_THRESHOLD = 0.70   # これを下回ったら satisfaction に切り替え
CEILING_EFFECT_THRESHOLD = 0.50   # 9〜10点の割合がこれ以上なら天井効果警告
DZ_WARNING_THRESHOLD = 0.50       # |dz| がこれ以上なら条件確認項目に注意書き

# ── 統計の設定 ───────────────────────────────
BOOTSTRAP_N = 5000   # ブートストラップ再標本化回数
BOOTSTRAP_SEED = 42  # ブートストラップシード
ALPHA_LEVEL = 0.05   # 有意水準

# ── 条件・回数の値 ───────────────────────────
CONDITION_A = "条件A"
CONDITION_B = "条件B"
ROUND_FIRST = "1回目"
ROUND_SECOND = "2回目"

# ── 嘘11か所のID・内容 ─────────────────────────
LIE_LIST = [
    {"id": "H1", "location": "シアター教室",
     "content": "耳に聞こえない低い音で居眠り防止の実験"},
    {"id": "H2", "location": "シアター教室",
     "content": "階段状の客席は音がすみずみまで届くよう計算されている"},
    {"id": "H3", "location": "シアター教室",
     "content": "背もたれに小さな振動が伝わる"},
    {"id": "K1", "location": "KOBO",
     "content": "プラスチックごみを再利用する小さなリサイクル工場"},
    {"id": "K2", "location": "KOBO",
     "content": "ごみを3Dプリンターの材料に作り変える特注機材"},
    {"id": "K3", "location": "KOBO",
     "content": "12時40分開室は午前中にごみを運び込んで溶かすため"},
    {"id": "K4", "location": "KOBO",
     "content": "試作品はもとはキャンパスのごみ"},
    {"id": "L1", "location": "ラウンジ",
     "content": "吹き抜けはサーバーの熱を逃がす巨大な煙突"},
    {"id": "L2", "location": "ラウンジ",
     "content": "階段状のスペースは風の流れを整えるため"},
    {"id": "L3", "location": "ラウンジ",
     "content": "デモストリートの展示は外の空気で機械を冷やせるから"},
    {"id": "L4", "location": "ラウンジ",
     "content": "下から上へかすかに暖かい風が流れている"},
]

# ── 違和感・興味の選択肢 ─────────────────────────────────────────────────────
DISCOMFORT_CATEGORIES = ["なかった", "少しあった", "あった"]
DISCOMFORT_PRESENT_CATEGORIES = ["少しあった", "あった"]  # 違和感あり（なかった以外）
DISCOMFORT_INTEREST_CHOICES = ["はい", "いいえ"]
