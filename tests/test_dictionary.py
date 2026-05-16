# SPDX-FileCopyrightText: 2026 Steve Gale <galesteven@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for dictionary filtering."""

from dictionary import filter_legal_guesses, load_words_from_file


def test_load_words_from_file_splits_by_length(tmp_path):
    word_file = tmp_path / "words.txt"
    word_file.write_text("crane\nrate\nate\n12345\nCROWN\n", encoding="utf-8")

    legal_guesses, one_char_less, two_chars_less = load_words_from_file(str(word_file), 5)

    assert legal_guesses == {"crane"}
    assert one_char_less == {"rate"}
    assert two_chars_less == {"ate"}


def test_filter_legal_guesses_removes_roman_numerals_not_words_and_non_answers():
    legal_guesses = {"cares", "cared", "mcm", "assoc", "moped", "crane"}
    non_answers = set()
    vulgar = {"moped"}
    one_char_less = {"care"}
    two_chars_less = {"car"}

    filtered_guesses, legal_answers = filter_legal_guesses(
        legal_guesses,
        non_answers,
        vulgar,
        5,
        one_char_less,
        two_chars_less,
    )

    assert filtered_guesses == {"cares", "cared", "moped", "crane"}
    assert "cared" in non_answers
    assert "mcm" not in filtered_guesses
    assert "assoc" not in filtered_guesses
    assert legal_answers == {"crane"}
