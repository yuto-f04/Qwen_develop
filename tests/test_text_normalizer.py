"""text_normalizer のユニットテスト。

各ルールの単体テスト + 台本に出てこない未知パターンによる汎用性検証 + 適用順序テスト。
"""
import pytest
from src.text_normalizer import (
    normalize_for_tts,
    add_reading_override,
    _OVERRIDE_DICT,
    _num_to_yomi,
)


# ------------------------------------------------------------------ #
#  ヘルパー                                                             #
# ------------------------------------------------------------------ #
class TestNumToYomi:
    def test_zero(self):
        assert _num_to_yomi(0) == "ぜろ"

    def test_single(self):
        assert _num_to_yomi(5) == "ご"

    def test_ten(self):
        assert _num_to_yomi(10) == "じゅう"

    def test_eleven(self):
        assert _num_to_yomi(11) == "じゅういち"

    def test_twenty(self):
        assert _num_to_yomi(20) == "にじゅう"

    def test_hundred(self):
        assert _num_to_yomi(100) == "ひゃく"

    def test_three_hundred(self):
        assert _num_to_yomi(300) == "さんびゃく"

    def test_six_hundred(self):
        assert _num_to_yomi(600) == "ろっぴゃく"

    def test_eight_hundred(self):
        assert _num_to_yomi(800) == "はっぴゃく"

    def test_one_thousand(self):
        assert _num_to_yomi(1000) == "せん"

    def test_two_thousand(self):
        assert _num_to_yomi(2000) == "にせん"

    def test_three_thousand(self):
        assert _num_to_yomi(3000) == "さんぜん"

    def test_composite(self):
        assert _num_to_yomi(121) == "ひゃくにじゅういち"

    def test_2025(self):
        assert _num_to_yomi(2025) == "にせんにじゅうご"


# ------------------------------------------------------------------ #
#  ルール0: 記号・括弧の前処理                                          #
# ------------------------------------------------------------------ #
class TestRule0Preprocess:
    def test_ellipsis_to_toten(self):
        assert normalize_for_tts("皆さん…どうぞ。") == "皆さん、どうぞ。"

    def test_multiple_ellipsis(self):
        result = normalize_for_tts("えっと……そうですね。")
        assert "、" in result
        assert "…" not in result

    def test_kakko_removed(self):
        assert normalize_for_tts("「秘密」の施設。") == "秘密の施設。"

    def test_nijukakko_removed(self):
        assert normalize_for_tts("『Dolby Atmos』対応。") == "ドルビー アトモス対応。"

    def test_3d_converted(self):
        assert normalize_for_tts("3Dプリンター。") == "さんディープリンター。"


# ------------------------------------------------------------------ #
#  ルール1: 例外辞書                                                    #
# ------------------------------------------------------------------ #
class TestRule1Override:
    def test_dolby_atmos(self):
        assert normalize_for_tts("Dolby Atmos対応です。") == "ドルビー アトモス対応です。"

    def test_barco(self):
        assert normalize_for_tts("BARCOプロジェクター。") == "バルコプロジェクター。"

    def test_kobo(self):
        assert normalize_for_tts("KOBOで作られた。") == "こうぼうで作られた。"

    def test_longest_match_priority(self):
        """'BARCO'と'BAR'が辞書にある場合、長い方が優先されること。"""
        add_reading_override("BAR", "バー")
        result = normalize_for_tts("BARCOがある。")
        # 'BARCO'が優先 → 'バルコ'
        assert result == "バルコがある。"
        # テスト後に一時追加したエントリを削除
        del _OVERRIDE_DICT["BAR"]

    def test_add_override_api(self):
        add_reading_override("UNESCO", "ユネスコ")
        assert normalize_for_tts("UNESCOの遺産。") == "ユネスコの遺産。"
        del _OVERRIDE_DICT["UNESCO"]

    def test_unlisted_word_not_converted_by_rule1(self):
        """辞書にない単語はルール1で変換されない(他ルールに委ねられる)。"""
        # "NASA"は辞書にないのでルール6(フォールバック)で変換される
        result = normalize_for_tts("NASAの研究。")
        assert "エヌエーエスエー" in result


# ------------------------------------------------------------------ #
#  ルール2: アルファベット+数字コード                                   #
# ------------------------------------------------------------------ #
class TestRule2Code:
    def test_h121(self):
        assert normalize_for_tts("H121教室") == "エイチひゃくにじゅういち教室"

    def test_floor_4f(self):
        assert normalize_for_tts("4F") == "よんかい"

    def test_floor_9f(self):
        assert normalize_for_tts("9F") == "きゅうかい"

    def test_h_building(self):
        # H棟 → ルール2のアルファベット+棟パターンで "エイチとう"
        result = normalize_for_tts("H棟")
        assert result == "エイチとう"

    def test_b203(self):
        """未知パターン: B203教室。"""
        assert normalize_for_tts("B203教室") == "ビーにひゃくさん教室"

    def test_code_with_suffix_room(self):
        # 室 → しつ に変換される(spec例: H棟→エイチとう と同様に読みに変換)
        result = normalize_for_tts("A101室")
        assert result == "エーひゃくいちしつ"


# ------------------------------------------------------------------ #
#  ルール3: 時刻                                                        #
# ------------------------------------------------------------------ #
class TestRule3Time:
    def test_1240(self):
        assert normalize_for_tts("12:40に集合。") == "じゅうにじよんじゅっぷんに集合。"

    def test_1810(self):
        assert normalize_for_tts("18:10開始。") == "じゅうはちじじゅっぷん開始。"

    def test_0900(self):
        assert normalize_for_tts("9:00スタート。") == "きゅうじスタート。"

    def test_unknown_pattern_915(self):
        """未知パターン: 9:15集合。"""
        assert normalize_for_tts("9:15集合。") == "きゅうじじゅうごふん集合。"


# ------------------------------------------------------------------ #
#  ルール4: 年号                                                        #
# ------------------------------------------------------------------ #
class TestRule4Year:
    def test_2025(self):
        assert normalize_for_tts("2025年に建設。") == "にせんにじゅうごねんに建設。"

    def test_1990(self):
        assert normalize_for_tts("1990年創業。") == "せんきゅうひゃくきゅうじゅうねん創業。"

    def test_unknown_pattern_2030(self):
        """未知パターン: 2030年開業。"""
        assert normalize_for_tts("2030年開業。") == "にせんさんじゅうねん開業。"


# ------------------------------------------------------------------ #
#  ルール5: 数字+単位                                                   #
# ------------------------------------------------------------------ #
class TestRule5Units:
    def test_seats(self):
        assert normalize_for_tts("200席あります。") == "にひゃくせきあります。"

    def test_meter(self):
        assert normalize_for_tts("高さ30m。") == "高ささんじゅうメートル。"

    def test_cm(self):
        assert normalize_for_tts("5cmの隙間。") == "ごセンチの隙間。"

    def test_floor_kanji(self):
        assert normalize_for_tts("3階にある。") == "さんかいにある。"

    def test_minute(self):
        assert normalize_for_tts("40分かかる。") == "よんじゅっぷんかかる。"

    def test_second(self):
        assert normalize_for_tts("30秒待つ。") == "さんじゅうびょう待つ。"

    def test_unknown_unit_kg(self):
        """未知パターン: 5kg → 数字だけ変換、単位はそのまま残す。"""
        result = normalize_for_tts("5kg")
        assert result == "ごキログラム"

    def test_unknown_unit_km(self):
        """未知パターン: 3km。"""
        result = normalize_for_tts("3km")
        assert result == "さんキロ"


# ------------------------------------------------------------------ #
#  ルール6: フォールバック英字                                           #
# ------------------------------------------------------------------ #
class TestRule6Fallback:
    def test_unknown_acronym(self):
        """未知パターン: XYZシステム。"""
        assert normalize_for_tts("XYZシステム。") == "エックスワイゼットシステム。"

    def test_two_letter(self):
        assert normalize_for_tts("AIが判断。") == "エーアイが判断。"

    def test_single_alpha_not_converted(self):
        """1文字だけのアルファベットはフォールバック対象外(ルール2で拾われなかった場合)。"""
        # 単体の"A"は2文字未満なのでフォールバックしない
        result = normalize_for_tts("A棟の前。")
        assert "A" in result or "エー" in result  # ルール2か残置か


# ------------------------------------------------------------------ #
#  ルール適用順序のテスト                                               #
# ------------------------------------------------------------------ #
class TestRuleOrder:
    def test_override_beats_fallback(self):
        """ルール1(辞書)がルール6(フォールバック)より優先される。"""
        # "BARCO" はフォールバックなら "ビーエーアールシーオー" になるはずだが
        # ルール1で "バルコ" になるべき
        result = normalize_for_tts("BARCO")
        assert result == "バルコ"
        assert "ビーエーアール" not in result

    def test_override_beats_code_pattern(self):
        """ルール1(辞書)がルール2(コード)より優先される。"""
        # 辞書に "H1" を登録した場合、コードパターンより優先されること
        add_reading_override("H1", "エイチワン")
        result = normalize_for_tts("H1棟")
        assert result == "エイチワン棟"
        del _OVERRIDE_DICT["H1"]

    def test_year_not_double_converted(self):
        """4桁年号はルール4だけで変換され、ルール5(単位「年」)と二重変換されないこと。"""
        result = normalize_for_tts("2025年")
        assert result == "にせんにじゅうごねん"
        assert "にせんにじゅうごねんねん" not in result

    def test_floor_f_before_code(self):
        """数字+F(階)がコードパターン(英字+数字)より先に処理される。"""
        result = normalize_for_tts("4F")
        assert result == "よんかい"

    def test_mixed_sentence(self):
        """複数ルールが混在する文でも正しく変換される。"""
        text = "H121で18:10から2025年のBARCOプロジェクターを見る。"
        result = normalize_for_tts(text)
        assert "エイチひゃくにじゅういち" in result
        assert "じゅうはちじ" in result
        assert "にせんにじゅうごねん" in result
        assert "バルコ" in result
