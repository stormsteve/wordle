# SPDX-FileCopyrightText: 2026 Steve Gale <galesteven@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for user interaction helpers."""

from __future__ import annotations

import logging

from config import Config
import user_interface


def test_validate_guess_input_rejects_wrong_length(caplog):
    Config().set_word_length(5)
    logger = logging.getLogger("test_validate_guess_input_rejects_wrong_length")

    with caplog.at_level(logging.ERROR):
        valid, last_guess = user_interface.validate_guess_input(
            "toolong", {"crane"}, logger, ""
        )

    assert valid is False
    assert last_guess == ""
    assert "does not have 5 letters" in caplog.text


def test_validate_guess_input_accepts_unknown_word_when_repeated():
    Config().set_word_length(5)
    logger = logging.getLogger("test_validate_guess_input_accepts_unknown_word_when_repeated")

    valid, last_guess = user_interface.validate_guess_input(
        "zzzzz", {"crane"}, logger, "zzzzz"
    )

    assert valid is True
    assert last_guess == "zzzzz"


def test_input_guess_retries_until_valid(monkeypatch, capsys):
    Config().set_word_length(5)
    guesses = iter(["nope", "crane"])
    monkeypatch.setattr(user_interface, "input_lower", lambda: next(guesses))

    result = user_interface.input_guess({"crane"})

    assert result == "crane"
    assert capsys.readouterr().out == "Guess> Guess> "


def test_get_user_clue_retries_until_valid(monkeypatch, capsys, caplog):
    Config().set_word_length(5)
    clues = iter(["gy", "gybxz", "gybgb"])
    monkeypatch.setattr(user_interface, "input_lower", lambda: next(clues))

    with caplog.at_level(logging.ERROR):
        result = user_interface.get_user_clue()

    assert result == ["g", "y", "b", "g", "b"]
    assert "Clue must be 5 letters long." in caplog.text
    assert "Clue must only contain g, y, and b." in caplog.text
    assert capsys.readouterr().out == "Clue [gyb]> Clue [gyb]> Clue [gyb]> "


def test_display_row_shows_guess_and_logic(capsys):
    Config().set_word_length(5)

    user_interface.display_row(2, ["g", "y", "b", "b", "g"], "crane", "accurate score=1.5")

    output = capsys.readouterr().out

    assert output.startswith("2 ")
    assert "C" in output
    assert "R" in output
    assert "A" in output
    assert "N" in output
    assert "E" in output
    assert "[accurate score=1.5]" in output


def test_display_board_renders_each_guess(monkeypatch):
    displayed_rows = []
    monkeypatch.setattr(
        user_interface,
        "display_row",
        lambda num, clue_list, guess, logic="": displayed_rows.append(
            (num, clue_list, guess, logic)
        ),
    )

    class FakeClues:
        @staticmethod
        def get_guesses():
            return ["crane", "slate"]

    user_interface.display_board(FakeClues(), "crane")

    assert displayed_rows == [
        (1, ["g", "g", "g", "g", "g"], "crane", ""),
        (2, ["b", "b", "g", "b", "g"], "slate", ""),
    ]
