# SPDX-FileCopyrightText: 2026 Steven M. Gale
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for game mode behavior."""

from __future__ import annotations

import logging

from config import Config
from logic import Logic
import game_modes
import user_interface


def test_mode_get_clue_uses_answer_when_available():
    Config().set_word_length(5)

    assert game_modes.Mode.get_clue("crate", "trace") == ["y", "g", "g", "y", "g"]


def test_mode_get_clue_prompts_user_when_answer_unknown(monkeypatch):
    monkeypatch.setattr(
        user_interface,
        "get_user_clue",
        lambda: ["g", "b", "b", "b", "b"],
    )

    result = game_modes.Mode.get_clue("crane", "")

    assert result == ["g", "b", "b", "b", "b"]


def test_mode_advise_print_raw_guess_includes_logic(capsys):
    logic = Logic()
    logic.update("accurate", 1.25, {"crane"})

    returned_logic = game_modes.ModeAdvise.print_raw_guess("crane", 2, logic)

    assert returned_logic is logic
    assert "2 Recommendation: CRANE [accurate score=1.25, len=1" in capsys.readouterr().out


def test_mode_advise_uses_start_word_for_first_turn(monkeypatch):
    config = Config()
    config.set_start("crane")
    config.set_word_length(5)

    monkeypatch.setattr(game_modes, "input_guess", lambda dictionary: "slate", raising=False)
    monkeypatch.setattr(game_modes, "accurate", lambda words, guess, limit: 2.5, raising=False)

    class FakeClues:
        @staticmethod
        def get_num_guesses():
            return 0

    logic = Logic()
    result = game_modes.ModeAdvise.get_user_guess(
        {"crane", "slate"},
        "slate",
        {"crane", "slate"},
        FakeClues(),
        logic,
    )

    assert result == "crane"
    assert logic.get_score() == 2.5
    assert "user input" in str(logic)


def test_mode_advise_uses_prompt_after_first_turn(monkeypatch):
    config = Config()
    config.set_start("crane")
    config.set_word_length(5)
    config.set_max_guesses(6)

    monkeypatch.setattr(game_modes, "input_guess", lambda dictionary: "slate", raising=False)
    monkeypatch.setattr(game_modes, "accurate", lambda words, guess, limit: 1.0, raising=False)

    class FakeClues:
        @staticmethod
        def get_num_guesses():
            return 1

    logic = Logic()
    result = game_modes.ModeAdvise.get_user_guess(
        {"crane", "slate"},
        "crane",
        {"crane", "slate"},
        FakeClues(),
        logic,
    )

    assert result == "slate"
    assert logic.get_score() == 1.0


def test_mode_play_delegates_to_mode_advise(monkeypatch):
    monkeypatch.setattr(
        game_modes.ModeAdvise,
        "get_user_guess",
        staticmethod(lambda dictionary, guess, words, clues, logic: "crane"),
    )

    result = game_modes.ModePlay.get_user_guess({"crane"}, "slate", {"crane"}, object(), Logic())

    assert result == "crane"
