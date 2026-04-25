from __future__ import annotations

import unittest

from reddit_rag.processing.text_clean import clean_reddit_text


class CleanRedditTextTests(unittest.TestCase):
    def test_deleted_and_removed_whole_body_only(self) -> None:
        for raw in ("[deleted]", "  [removed]  ", "\ufeff[deleted]"):
            self.assertEqual(clean_reddit_text(raw), "")

    def test_deleted_token_inside_sentence_preserved(self) -> None:
        text = 'The automod left a placeholder saying "[deleted]" but the rest is fine.'
        self.assertEqual(clean_reddit_text(text), text)

    def test_urls_preserve_trailing_paren_and_bracket(self) -> None:
        line_a = "See https://example.com/wiki/Foo_(disambiguation)) for more."
        line_b = "Link https://example.com/path] end."
        self.assertEqual(clean_reddit_text(line_a), line_a)
        self.assertEqual(clean_reddit_text(line_b), line_b)

    def test_double_newlines_preserved_three_plus_collapsed(self) -> None:
        two_para = "first\n\nsecond"
        self.assertEqual(clean_reddit_text(two_para), two_para)
        many = "a\n\n\n\nb"
        self.assertEqual(clean_reddit_text(many), "a\n\nb")

    def test_double_quoted_phrase_preserved(self) -> None:
        text = 'He said "do not break this" and left.'
        self.assertEqual(clean_reddit_text(text), text)

    def test_blockquote_prefix_preserved(self) -> None:
        text = "> quoted line\nnot quoted"
        self.assertEqual(clean_reddit_text(text), text)

    def test_invisible_chars_removed_visible_unchanged(self) -> None:
        raw = "hello\u200b \u2060world\ufeff"
        self.assertEqual(clean_reddit_text(raw), "hello world")

    def test_whitespace_only_becomes_empty(self) -> None:
        self.assertEqual(clean_reddit_text("   \n\t  "), "")


if __name__ == "__main__":
    unittest.main()
