"""TTSに渡す直前の読み正規化モジュール。

台本テキストの表記は変更せず、このモジュール内でのみ変換する。
ルール適用順: 1(例外辞書) → 2(コード表記) → 3(時刻) → 4(年号) → 5(数字+単位) → 6(フォールバック英字)
"""
import re
from typing import Dict

# ------------------------------------------------------------------ #
#  アルファベット読みテーブル                                           #
# ------------------------------------------------------------------ #
_ALPHA_READING: Dict[str, str] = {
    "A": "エー", "B": "ビー", "C": "シー", "D": "ディー", "E": "イー",
    "F": "エフ", "G": "ジー", "H": "エイチ", "I": "アイ", "J": "ジェー",
    "K": "ケー", "L": "エル", "M": "エム", "N": "エヌ", "O": "オー",
    "P": "ピー", "Q": "キュー", "R": "アール", "S": "エス", "T": "ティー",
    "U": "ユー", "V": "ブイ", "W": "ダブリュー", "X": "エックス",
    "Y": "ワイ", "Z": "ゼット",
}


def _alpha_to_kana(s: str) -> str:
    """アルファベット文字列を1文字ずつカタカナ読みに変換する。"""
    return "".join(_ALPHA_READING.get(c.upper(), c) for c in s)


# ------------------------------------------------------------------ #
#  数字→日本語読み変換                                                 #
# ------------------------------------------------------------------ #
_DIGIT = ["", "いち", "に", "さん", "よん", "ご", "ろく", "なな", "はち", "きゅう"]
_TENS = ["", "じゅう", "にじゅう", "さんじゅう", "よんじゅう",
         "ごじゅう", "ろくじゅう", "ななじゅう", "はちじゅう", "きゅうじゅう"]
_ZERO = "ぜろ"


def _num_to_yomi(n: int) -> str:
    """0〜9999 の整数を日本語読みに変換する。"""
    if n == 0:
        return _ZERO
    if n < 10:
        return _DIGIT[n]
    if n < 100:
        tens = n // 10
        ones = n % 10
        t = "じゅう" if tens == 1 else _TENS[tens]
        return t + (_DIGIT[ones] if ones else "")
    if n < 1000:
        hundreds = n // 100
        rest = n % 100
        h = "ひゃく" if hundreds == 1 else (
            "にひゃく" if hundreds == 2 else
            "さんびゃく" if hundreds == 3 else
            "よんひゃく" if hundreds == 4 else
            "ごひゃく" if hundreds == 5 else
            "ろっぴゃく" if hundreds == 6 else
            "ななひゃく" if hundreds == 7 else
            "はっぴゃく" if hundreds == 8 else
            "きゅうひゃく"
        )
        return h + (_num_to_yomi(rest) if rest else "")
    # 1000〜9999
    thousands = n // 1000
    rest = n % 1000
    t = "せん" if thousands == 1 else (
        "にせん" if thousands == 2 else
        "さんぜん" if thousands == 3 else
        "よんせん" if thousands == 4 else
        "ごせん" if thousands == 5 else
        "ろくせん" if thousands == 6 else
        "ななせん" if thousands == 7 else
        "はっせん" if thousands == 8 else
        "きゅうせん"
    )
    return t + (_num_to_yomi(rest) if rest else "")


# ------------------------------------------------------------------ #
#  ルール1: 例外辞書                                                    #
# ------------------------------------------------------------------ #
_OVERRIDE_DICT: Dict[str, str] = {
    "Dolby Atmos Cinema": "ドルビー アトモス シネマ",
    "Dolby Atmos": "ドルビー アトモス",
    "BARCO": "バルコ",
    "JBL": "ジェイビーエル",
    "KOBO": "こうぼう",
    "4K": "よんケー",
    "3D": "さんディー",
}


def add_reading_override(word: str, reading: str) -> None:
    """例外辞書にエントリを追加する。"""
    _OVERRIDE_DICT[word] = reading


def _apply_override(text: str) -> str:
    """長い文字列を優先して例外辞書を適用する。"""
    for word in sorted(_OVERRIDE_DICT, key=len, reverse=True):
        text = text.replace(word, _OVERRIDE_DICT[word])
    return text


# ------------------------------------------------------------------ #
#  ルール2: アルファベット+数字のコード表記                             #
# ------------------------------------------------------------------ #
_SUFFIX_READING = {"棟": "とう", "階": "かい", "号": "ごう", "室": "しつ", "館": "かん"}

# \b は Unicode 文字(日本語等)との境界では機能しないため lookahead/lookbehind で代替
# 英字1〜3文字 + 数字1〜3桁 + 任意の末尾漢字
_CODE_PATTERN = re.compile(
    r"(?<![A-Za-z\d])([A-Za-z]{1,3})(\d{1,3})([棟階号室館]?)(?![A-Za-z\d])"
)
# 英字1〜3文字 + 棟/館 (数字なし) — 例: H棟, A館
_ALPHA_BUILDING_PATTERN = re.compile(
    r"(?<![A-Za-z\d])([A-Za-z]{1,3})([棟館])(?![A-Za-z\d])"
)
# 数字1〜3桁 + F (階数) — "4F" "9F" のみ
_FLOOR_PATTERN = re.compile(r"(?<!\d)(\d{1,3})([Ff])(?![A-Za-z\d])")


def _apply_code(text: str) -> str:
    def _replace_floor(m: re.Match) -> str:
        return _num_to_yomi(int(m.group(1))) + "かい"

    def _replace_alpha_building(m: re.Match) -> str:
        alpha_yomi = _alpha_to_kana(m.group(1))
        suffix_yomi = _SUFFIX_READING.get(m.group(2), m.group(2))
        return alpha_yomi + suffix_yomi

    def _replace_code(m: re.Match) -> str:
        alpha_yomi = _alpha_to_kana(m.group(1))
        num_yomi = _num_to_yomi(int(m.group(2)))
        suffix_yomi = _SUFFIX_READING.get(m.group(3), m.group(3))
        return alpha_yomi + num_yomi + suffix_yomi

    text = _FLOOR_PATTERN.sub(_replace_floor, text)
    text = _ALPHA_BUILDING_PATTERN.sub(_replace_alpha_building, text)
    text = _CODE_PATTERN.sub(_replace_code, text)
    return text


# ------------------------------------------------------------------ #
#  ルール3: 時刻表記 HH:MM                                             #
# ------------------------------------------------------------------ #
_TIME_PATTERN = re.compile(r"(?<!\d)(\d{1,2}):(\d{2})(?!\d)")

_MINUTE_IRREGULAR: Dict[int, str] = {
    1: "いっぷん", 3: "さんぷん", 4: "よんぷん", 6: "ろっぷん",
    8: "はっぷん", 10: "じゅっぷん", 13: "じゅうさんぷん",
    20: "にじゅっぷん", 30: "さんじゅっぷん", 40: "よんじゅっぷん",
}


def _minute_yomi(m: int) -> str:
    if m in _MINUTE_IRREGULAR:
        return _MINUTE_IRREGULAR[m]
    # 一般形: 数字読み + ふん
    return _num_to_yomi(m) + "ふん"


def _apply_time(text: str) -> str:
    def _replace(m: re.Match) -> str:
        h = int(m.group(1))
        mins = int(m.group(2))
        h_yomi = _num_to_yomi(h) + "じ"
        m_yomi = (_minute_yomi(mins) if mins else "")
        return h_yomi + m_yomi

    return _TIME_PATTERN.sub(_replace, text)


# ------------------------------------------------------------------ #
#  ルール4: 年号表記 YYYY年                                            #
# ------------------------------------------------------------------ #
_YEAR_PATTERN = re.compile(r"(\d{4})年")


def _apply_year(text: str) -> str:
    def _replace(m: re.Match) -> str:
        return _num_to_yomi(int(m.group(1))) + "ねん"

    return _YEAR_PATTERN.sub(_replace, text)


# ------------------------------------------------------------------ #
#  ルール5: 数字+単位・助数詞                                           #
# ------------------------------------------------------------------ #
# 助数詞テーブル: (パターン文字列, 変換関数 or 読み文字列)
def _unit_hon(n: int) -> str:
    special = {1: "いっぽん", 3: "さんぼん", 6: "ろっぽん", 8: "はっぽん", 10: "じゅっぽん"}
    return special.get(n, _num_to_yomi(n) + "ほん")


def _unit_mai(n: int) -> str:
    return _num_to_yomi(n) + "まい"


def _unit_ko(n: int) -> str:
    special = {1: "いっこ", 6: "ろっこ", 8: "はっこ", 10: "じゅっこ"}
    return special.get(n, _num_to_yomi(n) + "こ")


_UNIT_TABLE = [
    # (単位文字列, 変換関数)  — 長い単位を先に並べる(先勝ち)
    ("cm", lambda n: _num_to_yomi(n) + "センチ"),
    ("km", lambda n: _num_to_yomi(n) + "キロ"),
    ("kg", lambda n: _num_to_yomi(n) + "キログラム"),
    ("mg", lambda n: _num_to_yomi(n) + "ミリグラム"),
    ("m",  lambda n: _num_to_yomi(n) + "メートル"),
    ("席", lambda n: _num_to_yomi(n) + "せき"),
    ("階", lambda n: _num_to_yomi(n) + "かい"),
    ("年", None),   # ルール4で処理済み → スキップ
    ("分", lambda n: _minute_yomi(n)),
    ("秒", lambda n: _num_to_yomi(n) + "びょう"),
    ("本", _unit_hon),
    ("枚", _unit_mai),
    ("個", _unit_ko),
]

# 数字+単位パターンを動的に構築
_units_escaped = "|".join(
    re.escape(u) for u, _ in _UNIT_TABLE if u != "年"
)
_UNIT_PATTERN = re.compile(rf"(\d+)({_units_escaped})")


def _apply_units(text: str) -> str:
    unit_map = {u: fn for u, fn in _UNIT_TABLE}

    def _replace(m: re.Match) -> str:
        n = int(m.group(1))
        unit = m.group(2)
        fn = unit_map.get(unit)
        if fn is None:
            return m.group(0)
        return fn(n)

    return _UNIT_PATTERN.sub(_replace, text)


# ------------------------------------------------------------------ #
#  ルール0: 記号・括弧の前処理                                          #
# ------------------------------------------------------------------ #
# 三点リーダー・中黒連続 → 読点（ポーズとして扱う）
_ELLIPSIS_PATTERN = re.compile(r"[…・]{1,}")
# 読点が句点・感嘆符・疑問符の直前にある場合 → 読点を除去（「数々…。」→「数々。」）
_COMMA_BEFORE_PERIOD = re.compile(r"、([。！!?？])")
# 装飾括弧（読まなくてよい）→ 除去
_BRACKET_PATTERN = re.compile(r"[「」『』【】［］〔〕]")


def _apply_preprocess(text: str) -> str:
    text = _ELLIPSIS_PATTERN.sub("、", text)
    text = _COMMA_BEFORE_PERIOD.sub(r"\1", text)
    text = _BRACKET_PATTERN.sub("", text)
    return text


# ------------------------------------------------------------------ #
#  ルール6: フォールバック(未知の連続英字)                              #
# ------------------------------------------------------------------ #
_FALLBACK_ALPHA = re.compile(r"[A-Za-z]{2,}")


def _apply_fallback(text: str) -> str:
    return _FALLBACK_ALPHA.sub(lambda m: _alpha_to_kana(m.group()), text)


# ------------------------------------------------------------------ #
#  メイン正規化関数                                                     #
# ------------------------------------------------------------------ #
def normalize_for_tts(text: str) -> str:
    """台本テキストをTTS向け読み上げ文字列に変換する。

    適用順: 0(記号前処理) → 1(例外辞書) → 2(コード) → 3(時刻) → 4(年号) → 5(単位) → 6(フォールバック)
    """
    text = _apply_preprocess(text)
    text = _apply_override(text)
    text = _apply_code(text)
    text = _apply_time(text)
    text = _apply_year(text)
    text = _apply_units(text)
    text = _apply_fallback(text)
    return text
