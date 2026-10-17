# SPDX-FileCopyrightText: 2026 Steven M. Gale
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for accumulated clue filtering."""

from clue_list import get_clue_list
from clues import Clues
import pytest


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


def test_conflicting_green_clues_make_all_candidates_impossible():
    clues = Clues()
    clues.add_clue('crane', list('gbbbb'))
    clues.add_clue('sloth', list('gbbbb'))

    assert not clues.is_possible_word('sissy')
    assert clues.filter_words({'sissy', 'civic'}) == set()


@pytest.mark.parametrize('guess,answer,candidate', [
    ('sassy', 'aside', 'abuse'),
    ('allee', 'apple', 'axlxe'),
])
def test_gray_duplicates_exclude_their_positions(guess, answer, candidate):
    clues = Clues()
    clues.add_clue(guess, get_clue_list(guess, answer))
    assert clues.is_possible_word(answer)
    assert not clues.is_possible_word(candidate)


def test_duplicate_filter_matches_feedback_over_multiple_rounds():
    words = {'sassy', 'aside', 'abuse', 'apple', 'allee', 'eerie', 'refer', 'array'}
    for answer in words:
        clues = Clues()
        expected = words.copy()
        for guess in ('sassy', 'allee', 'eerie'):
            feedback = get_clue_list(guess, answer)
            clues.add_clue(guess, feedback)
            expected = {word for word in expected if get_clue_list(guess, word) == feedback}
            assert clues.filter_words(words) == expected


def test_clues_keep_answers_valid_after_multiple_duplicate_letter_clues():
    answers = ["allee", "apple", "eerie", "refer", "sassy", "civic", "array"]
    guesses = ["allee", "eerie", "sassy", "civic", "array", "refer"]

    for answer in answers:
        clues = Clues()
        for guess in guesses[:2]:
            clues.add_clue(guess, get_clue_list(guess, answer))

        assert clues.is_possible_word(answer), (answer, repr(clues))


def test_filter_words_len_returns_max_score_after_limit():
    clues = Clues()
    words = {"cigar", "rebut", "sissy"}

    assert clues.filter_words_len(words, limit=1) == 9999
