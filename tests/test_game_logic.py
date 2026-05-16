# SPDX-FileCopyrightText: 2026 Steve Gale <galesteven@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Integration-style tests for the main game flow."""

from __future__ import annotations

from logic import Logic
from config import Config
import game_logic
import user_interface
import best_guess as best_guess_module


def test_initialize_game_picks_random_answer_when_needed(monkeypatch):
    config = Config()
    config.set_mode("auto")
    config.set_answer("")
    config.set_start("crane")
    config.set_word_length(5)

    monkeypatch.setattr(
        game_logic,
        "build_dictionaries",
        lambda: ({"crane", "slate"}, {"crane", "slate"}),
    )
    monkeypatch.setattr(game_logic, "random_word", lambda words: "slate")

    (
        legal_guesses,
        legal_answers,
        clues,
        answer,
        guess,
        logic,
        mode_class,
    ) = game_logic.initialize_game()

    assert legal_guesses == {"crane", "slate"}
    assert legal_answers == {"crane", "slate"}
    assert clues.get_num_guesses() == 0
    assert answer == "slate"
    assert guess == "crane"
    assert logic.get_score() == 0
    assert mode_class.__name__ == "Mode"
    assert config.get_answer() == "slate"


def test_execute_game_rounds_solves_on_first_guess(monkeypatch, capsys):
    config = Config()
    config.set_mode("auto")
    config.set_word_length(5)
    config.set_max_guesses(3)

    displayed_rows = []
    monkeypatch.setattr(
        user_interface,
        "display_row",
        lambda row, clue_list, guess, logic="": displayed_rows.append(
            (row, clue_list, guess, logic)
        ),
    )

    class SolvedMode:
        @staticmethod
        def print_raw_guess(guess, row_num, logic):
            return logic

        @staticmethod
        def get_user_guess(legal_guesses, guess, legal_answers, clues, logic):
            return guess

        @staticmethod
        def get_clue(guess, answer):
            return ["g"] * 5

    result = game_logic.execute_game_rounds(
        {"crane"},
        {"crane"},
        game_logic.Clues(),
        "crane",
        "crane",
        Logic(),
        SolvedMode,
    )

    assert result == "crane"
    assert displayed_rows == [(1, ["g", "g", "g", "g", "g"], "crane", " score=0.00, len=0")]
    assert "Solved for CRANE in 1 guesses" in capsys.readouterr().out


def test_execute_game_rounds_uses_best_guess_and_shows_answer_on_failure(monkeypatch, capsys):
    config = Config()
    config.set_mode("auto")
    config.set_word_length(5)
    config.set_max_guesses(2)

    displayed_rows = []
    monkeypatch.setattr(
        user_interface,
        "display_row",
        lambda row, clue_list, guess, logic="": displayed_rows.append(
            (row, clue_list, guess, logic)
        ),
    )

    next_logic = Logic()
    next_logic.update("accurate", 1.5, {"crane"})
    best_guess_calls = []

    def fake_best_guess(legal_guesses, legal_answers, clues):
        best_guess_calls.append((set(legal_guesses), set(legal_answers), clues.get_num_guesses()))
        return "crane", next_logic

    monkeypatch.setattr(best_guess_module, "best_guess", fake_best_guess)

    clue_map = {
        "slate": ["b", "b", "b", "b", "b"],
        "crane": ["b", "b", "b", "b", "b"],
    }

    class TwoRoundMode:
        @staticmethod
        def print_raw_guess(guess, row_num, logic):
            return logic

        @staticmethod
        def get_user_guess(legal_guesses, guess, legal_answers, clues, logic):
            return guess

        @staticmethod
        def get_clue(guess, answer):
            return clue_map[guess]

    result = game_logic.execute_game_rounds(
        {"slate", "crane"},
        {"crane"},
        game_logic.Clues(),
        "crane",
        "slate",
        Logic(),
        TwoRoundMode,
    )

    output = capsys.readouterr().out

    assert result == "crane"
    assert len(displayed_rows) == 2
    assert displayed_rows[0][0:3] == (1, ["b", "b", "b", "b", "b"], "slate")
    assert displayed_rows[1][0:3] == (2, ["b", "b", "b", "b", "b"], "crane")
    assert best_guess_calls == [({"slate", "crane"}, set(), 1)]
    assert "Better luck next time!" in output
    assert "The answer is: CRANE" in output


def test_game_loop_displays_board_with_final_guess_when_answer_is_unknown(monkeypatch):
    displayed = []

    monkeypatch.setattr(
        game_logic,
        "initialize_game",
        lambda: (
            {"crane"},
            {"crane"},
            game_logic.Clues(),
            "",
            "slate",
            Logic(),
            object,
        ),
    )
    monkeypatch.setattr(game_logic, "execute_game_rounds", lambda *args: "crane")
    monkeypatch.setattr(
        user_interface,
        "display_board",
        lambda clues, answer: displayed.append((clues, answer)),
    )

    game_logic.game_loop()

    assert len(displayed) == 1
    assert displayed[0][1] == "crane"
