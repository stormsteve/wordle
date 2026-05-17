# SPDX-FileCopyrightText: 2026 Steven M. Gale
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for clue generation helpers."""

from clue_list import get_clue_list, replace_first


def test_replace_first_replaces_only_the_first_matching_letter():
    letters = ["a", "b", "a"]

    result = replace_first(letters, "a", "1")

    assert result == ["1", "b", "a"]


def test_get_clue_list_marks_green_yellow_and_black_letters():
    assert get_clue_list("crate", "trace") == ["y", "g", "g", "y", "g"]


def test_get_clue_list_handles_duplicate_letters_without_double_counting():
    assert get_clue_list("allee", "apple") == ["g", "y", "b", "b", "g"]
