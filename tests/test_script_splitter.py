import pytest
from src.script_splitter import split_into_sentences


class TestSplitIntoSentences:
    def test_split_on_kuten(self):
        result = split_into_sentences("こんにちは。ありがとう。")
        assert result == ["こんにちは。", "ありがとう。"]

    def test_split_on_exclamation_fullwidth(self):
        result = split_into_sentences("すごい！やった！")
        assert result == ["すごい！", "やった！"]

    def test_split_on_question_fullwidth(self):
        result = split_into_sentences("本当？そうなの？")
        assert result == ["本当？", "そうなの？"]

    def test_split_on_question_ascii(self):
        result = split_into_sentences("Really?OK.")
        assert result == ["Really?", "OK."]

    def test_no_split_on_toten(self):
        result = split_into_sentences("赤い、青い。白い。")
        assert result == ["赤い、青い。", "白い。"]

    def test_delimiter_remains_at_end(self):
        result = split_into_sentences("はい。いいえ。")
        assert all(s.endswith("。") for s in result)

    def test_newlines_removed(self):
        result = split_into_sentences("こんにちは。\nありがとう。")
        assert result == ["こんにちは。", "ありがとう。"]

    def test_empty_parts_removed(self):
        # 末尾に空白だけが残る場合は除去される
        result = split_into_sentences("こんにちは。  ")
        assert result == ["こんにちは。"]

    def test_empty_string(self):
        result = split_into_sentences("")
        assert result == []

    def test_whitespace_only(self):
        result = split_into_sentences("   ")
        assert result == []

    def test_mixed_delimiters(self):
        result = split_into_sentences("本当に？ありがとう！よかった。")
        assert result == ["本当に？", "ありがとう！", "よかった。"]

    def test_long_sentence_with_toten(self):
        sentence = "皆さん、本日は、キャンパスへようこそ。ありがとう。"
        result = split_into_sentences(sentence)
        assert result == ["皆さん、本日は、キャンパスへようこそ。", "ありがとう。"]
