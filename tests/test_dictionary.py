# SPDX-FileCopyrightText: 2026 Steven M. Gale
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for dictionary filtering."""

import dictionary
from config import Config
from dictionary import filter_legal_guesses, load_words_from_file


def test_load_words_from_file_splits_by_length(tmp_path):
    word_file = tmp_path / "words.txt"
    word_file.write_text("crane\nrate\nate\n12345\nCROWN\n", encoding="utf-8")

    legal_guesses, one_char_less, two_chars_less = load_words_from_file(str(word_file), 5)

    assert legal_guesses == {"crane"}
    assert one_char_less == {"rate"}
    assert two_chars_less == {"ate"}


def test_bundled_word_files_are_resolved_from_module_directory(monkeypatch, tmp_path):
    bundled_file = tmp_path / "bundled.txt"
    bundled_file.write_text("crane\n", encoding="utf-8")
    working_directory = tmp_path / "working-directory"
    working_directory.mkdir()
    monkeypatch.setattr(dictionary, "__file__", str(tmp_path / "dictionary.py"))
    monkeypatch.chdir(working_directory)

    assert dictionary.load_word_set_from_file("bundled.txt") == {"crane"}


def test_default_dictionaries_are_available_outside_working_directory(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    legal_guesses, legal_answers = dictionary.build_dictionaries()

    assert legal_guesses == dictionary.load_word_set_from_file("legal_guesses.txt")
    assert legal_answers == dictionary.load_word_set_from_file("legal_answers.txt")
    assert len(legal_guesses) > len(legal_answers)
    assert Config().get_word_list_dictionary() == "legal_guesses.txt"


def test_default_dictionary_uses_source_list_for_other_word_lengths(tmp_path):
    source_file = tmp_path / "words.txt"
    source_file.write_text("abcdefgh\nabcdefg\nabcdef\n", encoding="utf-8")
    config = Config()
    config.set_word_length(8)
    config.set_word_list_dictionary2(str(source_file))

    legal_guesses, legal_answers = dictionary.build_dictionaries()

    assert legal_guesses == {"abcdefgh"}
    assert legal_answers == {"abcdefgh"}


def test_other_word_lengths_fall_back_to_american_english(monkeypatch, tmp_path):
    (tmp_path / "american-english").write_text(
        "abcdefgh\nabcdefg\nabcdef\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    config = Config()
    config.set_word_length(8)
    config.set_word_list_dictionary2("missing-words")

    legal_guesses, legal_answers = dictionary.build_dictionaries()

    assert legal_guesses == {"abcdefgh"}
    assert legal_answers == {"abcdefgh"}


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
