# SPDX-FileCopyrightText: 2026 Steve Gale <galesteven@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for best-guess selection behavior."""

from __future__ import annotations

from config import Config
from clues import Clues
from logic import Logic
import best_guess


def test_get_cached_guess_returns_logic_when_cache_hit(monkeypatch):
    config = Config()
    config.set_use_cache(True)
    clues = Clues()
    clues.add_clue("crane", ["g", "g", "g", "g", "g"])

    class FakeCache:
        @staticmethod
        def in_cache(clues_obj):
            return True

        @staticmethod
        def get(clues_obj):
            return ("slate", 1.75)

    monkeypatch.setattr(best_guess, "SecondGuessCache", FakeCache)

    guess, logic = best_guess.get_cached_guess(clues, {"crane", "slate"})

    assert guess == "slate"
    assert logic.get_score() == 1.75
    assert "cache lookup" in str(logic)


def test_select_guess_set_prefers_remaining_answers_near_endgame(monkeypatch):
    config = Config()
    config.set_max_guesses(6)
    monkeypatch.setattr(best_guess, "vulgar_words", lambda: {"vulgar"})

    class FakeClues:
        @staticmethod
        def get_num_guesses():
            return 5

    result = best_guess.select_guess_set(
        {"crane", "slate", "vulgar"},
        {"crane", "slate"},
        FakeClues(),
    )

    assert result == {"crane", "slate"}


def test_select_guess_set_uses_dictionary_minus_vulgar_words_early(monkeypatch):
    config = Config()
    config.set_max_guesses(6)
    monkeypatch.setattr(best_guess, "vulgar_words", lambda: {"vulgar"})

    class FakeClues:
        @staticmethod
        def get_num_guesses():
            return 1

    result = best_guess.select_guess_set(
        {"crane", "slate", "vulgar"},
        {"crane", "slate", "glare"},
        FakeClues(),
    )

    assert result == {"crane", "slate"}


def test_find_best_guess_returns_all_minimum_scoring_candidates(monkeypatch):
    monkeypatch.setattr(
        best_guess,
        "process_accurate_logic",
        lambda all_guesses, words: {"crane": 1.0, "slate": 2.0, "glare": 1.0},
    )

    best_guesses, score = best_guess.find_best_guess(
        {"crane", "slate", "glare"},
        {"crane", "slate"},
    )

    assert set(best_guesses) == {"crane", "glare"}
    assert score == 1.0


def test_resolve_guess_ties_uses_meta_scores_then_random_choice(monkeypatch):
    config = Config()
    from algorithm import accurate_avg

    config.set_algorithm(accurate_avg)

    import algorithm

    monkeypatch.setattr(algorithm, "accurate_median", lambda words, guess, limit: {"crane": 3.0, "slate": 1.0}[guess])
    monkeypatch.setattr(algorithm, "accurate_max", lambda words, guess, limit: {"crane": 2.0, "slate": 1.0}[guess])

    chosen = []

    def fake_choice(candidates):
        chosen.append(list(candidates))
        return candidates[0]

    import random
    monkeypatch.setattr(random, "choice", fake_choice)

    result = best_guess.resolve_guess_ties(["crane", "slate"], {"crane", "slate"})

    assert result == "slate"
    assert chosen == [["slate"]]


def test_best_guess_returns_unknown_word_for_empty_solution_space():
    config = Config()
    config.set_word_length(5)

    guess, logic = best_guess.best_guess({"crane"}, set(), Clues())

    assert guess == "unkno"
    assert logic.get_score() == 0
    assert "unknown word" in str(logic)


def test_best_guess_returns_cached_guess_before_scoring(monkeypatch):
    cached_logic = Logic()
    cached_logic.update("cache lookup", 0.75, {"slate"})

    monkeypatch.setattr(best_guess, "get_cached_guess", lambda clues, words: ("slate", cached_logic))
    monkeypatch.setattr(best_guess, "find_best_guess", lambda all_guesses, words: (_ for _ in ()).throw(AssertionError("should not score")))

    guess, logic = best_guess.best_guess({"crane", "slate"}, {"slate"}, Clues())

    assert guess == "slate"
    assert logic is cached_logic


def test_best_guess_uses_tie_breaker_when_multiple_best_guesses(monkeypatch):
    monkeypatch.setattr(best_guess, "get_cached_guess", lambda clues, words: None)
    monkeypatch.setattr(best_guess, "select_guess_set", lambda dictionary, words, clues: {"crane", "slate"})
    monkeypatch.setattr(best_guess, "find_best_guess", lambda all_guesses, words: (["crane", "slate"], 1.25))
    monkeypatch.setattr(best_guess, "resolve_guess_ties", lambda guesses, words: "slate")

    guess, logic = best_guess.best_guess({"crane", "slate"}, {"crane", "slate"}, Clues())

    assert guess == "slate"
    assert logic.get_score() == 1.25
    assert "accurate" in str(logic)
