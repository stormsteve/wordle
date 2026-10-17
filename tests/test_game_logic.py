# SPDX-FileCopyrightText: 2026 Steven M. Gale
# SPDX-License-Identifier: GPL-3.0-or-later

"""Integration-style tests for the main game flow."""

from __future__ import annotations

import logging
import pytest

from logic import Logic
from config import Config
import game_logic
import user_interface
import best_guess as best_guess_module


@pytest.mark.parametrize("mode", ["auto", "play", "clues", "advise"])
@pytest.mark.parametrize("answer", ["cat", "planet"])
def test_obtain_answer_rejects_wrong_length_in_every_mode(mode, answer, caplog):
    config = Config()
    config.set_mode(mode)
    config.set_word_length(5)
    config.set_answer(answer)

    with pytest.raises(SystemExit) as error:
        game_logic.obtain_answer({"crane"})

    assert error.value.code == 1
    assert "expected 5" in caplog.text


@pytest.mark.parametrize("mode", ["clues", "advise"])
@pytest.mark.parametrize("answer", [None, "", "crane"])
def test_obtain_answer_preserves_optional_answer_in_manual_modes(mode, answer):
    config = Config()
    config.set_mode(mode)
    config.set_answer(answer)

    assert game_logic.obtain_answer({"crane"}) == answer


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

    def fake_best_guess(legal_guesses, legal_answers, clues, all_answers):
        assert all_answers == {'crane'}
        best_guess_calls.append((set(legal_guesses), set(legal_answers), clues.get_num_guesses()))
        return "crane", next_logic

    monkeypatch.setattr(best_guess_module, "best_guess", fake_best_guess)

    clue_map = {
        "slate": ["b", "b", "g", "b", "g"],
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
    assert displayed_rows[0][0:3] == (1, ["b", "b", "g", "b", "g"], "slate")
    assert displayed_rows[1][0:3] == (2, ["b", "b", "b", "b", "b"], "crane")
    assert best_guess_calls == [({"slate", "crane"}, {"crane"}, 1)]
    assert "Better luck next time!" in output
    assert "The answer is: CRANE" in output


def test_execute_game_rounds_stops_when_clues_eliminate_all_answers(monkeypatch, caplog):
    Config().set_word_length(5)
    Config().set_max_guesses(6)
    monkeypatch.setattr(
        user_interface,
        "display_row",
        lambda *args: None,
    )

    class ContradictoryMode:
        @staticmethod
        def print_raw_guess(guess, row_num, logic):
            return logic

        @staticmethod
        def get_user_guess(legal_guesses, guess, legal_answers, clues, logic):
            return guess

        @staticmethod
        def get_clue(guess, answer):
            return list('ggggy')

    with pytest.raises(SystemExit) as error:
        game_logic.execute_game_rounds(
            {'crane'}, {'crane'}, game_logic.Clues(), '', 'crane', Logic(), ContradictoryMode)

    assert error.value.code == 1
    assert 'No answers match the clues provided.' in caplog.text


def test_game_loop_does_not_treat_final_guess_as_unknown_answer(monkeypatch):
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
    assert displayed[0][1] == ""


@pytest.mark.parametrize('start', ['toolong', 'cat'])
@pytest.mark.parametrize('level', [logging.ERROR, logging.DEBUG])
def test_wrong_length_start_is_rejected_even_in_debug(start, level):
    logger = logging.getLogger('starting-word')
    logger.setLevel(level)
    with pytest.raises(SystemExit) as error:
        game_logic.setup_initial_guess(start, 5, {'crane'}, {'crane'}, logger)
    assert error.value.code == 1
