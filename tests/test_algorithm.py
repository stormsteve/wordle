"""Tests for guess scoring algorithms."""

from __future__ import annotations

import math

from config import Config
import algorithm


def test_accurate_delegates_to_configured_algorithm():
    Config().set_algorithm(lambda words, guess, limit: 7.25)

    assert algorithm.accurate({"crane", "slate"}, "crane") == 7.25


def test_accurate_avg_returns_limit_for_empty_word_set():
    assert algorithm.accurate_avg(set(), "crane", 12.0) == 12.0


def test_accurate_avg_and_median_prefer_answer_words_over_non_answers():
    words = {"crane", "slate"}

    assert math.isclose(algorithm.accurate_avg(words, "crane"), 0.5)
    assert math.isclose(algorithm.accurate_avg(words, "adieu"), 2.1)
    assert math.isclose(algorithm.accurate_median(words, "crane"), 1.0)
    assert math.isclose(algorithm.accurate_median(words, "adieu"), 2.1)


def test_accurate_max_biases_non_answers_and_handles_single_answer_case():
    assert algorithm.accurate_max({"crane"}, "crane") == 1
    assert math.isclose(algorithm.accurate_max({"crane"}, "slate"), 1.1)


def test_accurate_algorithms_short_circuit_when_limit_is_exceeded():
    words = {"crane", "slate"}
    max_score = Config().get_max_word_score()

    assert algorithm.accurate_avg(words, "adieu", limit=0.5) == max_score
    assert algorithm.accurate_median(words, "adieu", limit=0.5) == max_score
    assert algorithm.accurate_max(words, "adieu", limit=0.5) == max_score
