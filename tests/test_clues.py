"""Tests for accumulated clue filtering."""

from clue_list import get_clue_list
from clues import Clues


def test_clues_filter_words_after_single_clue():
    clues = Clues()
    clues.add_clue("crate", get_clue_list("crate", "trace"))

    words = {"trace", "crate", "react", "grate"}

    assert clues.filter_words(words) == {"trace"}


def test_clues_reject_word_with_black_letter():
    clues = Clues()
    clues.add_clue("adieu", ["b", "b", "b", "b", "b"])

    assert clues.is_possible_word("story")
    assert not clues.is_possible_word("cigar")


def test_clues_track_duplicate_letter_bounds():
    clues = Clues()
    clues.add_clue("sassy", ["b", "g", "b", "b", "b"])

    assert clues.is_possible_word("mango")
    assert not clues.is_possible_word("class")
    assert not clues.is_possible_word("salsa")


def test_filter_words_len_returns_max_score_after_limit():
    clues = Clues()
    words = {"cigar", "rebut", "sissy"}

    assert clues.filter_words_len(words, limit=1) == 9999
