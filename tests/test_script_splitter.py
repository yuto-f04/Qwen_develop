import pytest
from src.script_splitter import split_into_sentences


class TestSplitIntoSentences:
    def test_split_on_kuten(self):
        result = split_into_sentences("こんにちは。ありがとう。")
        assert result == [("こんにちは。", 400), ("ありがとう。", 400)]

    def test_split_on_exclamation_fullwidth(self):
        result = split_into_sentences("すごい！やった！")
        assert result == [("すごい！", 400), ("やった！", 400)]

    def test_split_on_question_fullwidth(self):
        result = split_into_sentences("本当？そうなの？")
        assert result == [("本当？", 400), ("そうなの？", 400)]

    def test_split_on_question_ascii(self):
        result = split_into_sentences("Really?OK.")
        assert result == [("Really?", 400), ("OK.", 400)]

    def test_split_on_toten(self):
        # 読点でも分割する。読点後は短い無音になる
        result = split_into_sentences("赤い、青い。白い。")
        assert result == [("赤い、", 150), ("青い。", 400), ("白い。", 400)]

    def test_delimiter_remains_at_end(self):
        result = split_into_sentences("はい。いいえ。")
        texts = [t for t, _ in result]
        assert all(t.endswith("。") for t in texts)

    def test_newlines_removed(self):
        result = split_into_sentences("こんにちは。\nありがとう。")
        texts = [t for t, _ in result]
        assert texts == ["こんにちは。", "ありがとう。"]

    def test_empty_parts_removed(self):
        result = split_into_sentences("こんにちは。  ")
        assert result == [("こんにちは。", 400)]

    def test_empty_string(self):
        result = split_into_sentences("")
        assert result == []

    def test_whitespace_only(self):
        result = split_into_sentences("   ")
        assert result == []

    def test_mixed_delimiters(self):
        result = split_into_sentences("本当に？ありがとう！よかった。")
        assert result == [("本当に？", 400), ("ありがとう！", 400), ("よかった。", 400)]

    def test_long_sentence_with_toten(self):
        # 読点で複数に分割され、それぞれ短い無音になる
        result = split_into_sentences("皆さん、本日は、キャンパスへようこそ。ありがとう。")
        assert result == [
            ("皆さん、", 150),
            ("本日は、", 150),
            ("キャンパスへようこそ。", 400),
            ("ありがとう。", 400),
        ]

    def test_comma_silence_shorter_than_period_silence(self):
        # 読点後 < 句点後 であることを確認
        result = split_into_sentences("Aは、Bである。")
        silences = [ms for _, ms in result]
        assert silences == [150, 400]
        assert silences[0] < silences[1]

    def test_mixed_toten_and_kuten(self):
        result = split_into_sentences("この施設は、2025年に完成した。定員は200席だ。")
        texts = [t for t, _ in result]
        silences = [ms for _, ms in result]
        assert texts == ["この施設は、", "2025年に完成した。", "定員は200席だ。"]
        assert silences == [150, 400, 400]
