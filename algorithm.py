# SPDX-FileCopyrightText: 2026 Steven M. Gale
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Score candidate guesses against the current set of possible answers.

This module provides the core guess-rating algorithms used to compare Wordle
guesses, including average, median, and worst-case scoring strategies.
"""

from __future__ import annotations
import logging              # logging

from mytypes import WordSet            # My type hints
from config  import Config             # We need this for a configurable constant
from clues   import Clues              # Clues gathered so far
from clue_list import get_clue_list    # To generate a clue list


def _max_word_score() -> int:
    """Return the current configured max word score."""
    return Config().get_max_word_score()


def accurate(words: WordSet, guess: str, limit: float | None = None) -> float:
    """
    Calculate the accuracy score for a guess by simulating it against all possible answers.

    For each word in the set (except the guess itself), treat it as the answer and see how many
    words remain after filtering with the guess. The algorithm used comes from the config object.

    Args:
        words (WordSet): The current set of possible answers.
        guess (str): The guess word to evaluate.
        limit (float): Early termination limit for performance.

    Returns:
        float: The score for the guess. Smaller is better.
    """
    actual_limit = _max_word_score() if limit is None else limit
    return Config().get_algorithm()(words, guess, actual_limit)


def accurate_avg(words: WordSet, guess: str, limit: float | None = None) -> float:
    """
    Calculate the accuracy score for a guess by simulating it against all possible answers.

    For each word in the set (except the guess itself), treat it as the answer and see how many
    words remain after filtering with the guess. Returns the average remaining words, with a bias
    against guesses not in the answer set.

    Args:
        words (WordSet): The current set of possible answers.
        guess (str): The guess word to evaluate.
        limit (float): Early termination limit for performance.

    Returns:
        float: The average number of remaining words after the guess.
    """
    actual_limit = _max_word_score() if limit is None else limit
    if len(words) == 0:
        return actual_limit
    accum_score = 0
    accum_limit = actual_limit * len(words)
    for w in words:
        if w != guess: # Don't take into account the 1 that will exactly match
            temp_clue = Clues()
            temp_clue.add_clue(guess, get_clue_list(guess, w))
            accum_score += temp_clue.filter_words_len(words)
            # Short ciruit if the score is too high already
            if accum_score > accum_limit:
                return _max_word_score()
    # Return the average number of resulting words, with a bias against words
    # that cannot be the correct answer
    return accum_score / len(words)  + (0 if guess in words else 0.1)

from typing import List

def accurate_median(words: WordSet, guess: str, limit: float | None = None) -> float:
    """
    Calculate the accuracy score for a guess by simulating it against all possible answers.
    For each word in the set (except the guess itself), treat it as the answer and see how many
    words remain after filtering with the guess. Returns the median remaining words, with a bias
    against guesses not in the answer set.
    Args:
        words (WordSet): The current set of possible answers.
        guess (str): The guess word to evaluate.
        limit (float): Early termination limit for performance.
    Returns:
        float: The median number of remaining words after the guess.
    """
    actual_limit = _max_word_score() if limit is None else limit
    if len(words) == 0:
        return actual_limit
    remaining_counts: List[int] = []
    accum_score = 0
    accum_limit = actual_limit * len(words)
    for w in words:
        if w != guess:  # Don't take into account the one that will exactly match
            temp_clue = Clues()
            temp_clue.add_clue(guess, get_clue_list(guess, w))
            count = temp_clue.filter_words_len(words)
            remaining_counts.append(count)
            accum_score += count
            # Short circuit if the score is too high already
            if accum_score > accum_limit:
                return _max_word_score()
    
    # Calculate the median of remaining counts
    if not remaining_counts:
        return 0.0
    remaining_counts.sort()
    mid = len(remaining_counts) // 2
    if len(remaining_counts) % 2 == 0:
        median = (remaining_counts[mid - 1] + remaining_counts[mid]) / 2
    else:
        median = remaining_counts[mid]
    
    # Return the median number of resulting words, with a bias against words
    # that cannot be the correct answer
    return median + (0 if guess in words else 0.1)

def accurate_max(words: WordSet, guess: str, limit: float | None = None) -> float:
    """
    Calculate the accuracy score for a guess by simulating it against all possible answers.
    For each word in the set (except the guess itself), treat it as the answer and see how many
    words remain after filtering with the guess. Returns the maximum remaining words, with a bias
    against guesses not in the answer set, normaized so it will be comparable to the average.

    Args:
        words (WordSet): The current set of possible answers.
        guess (str): The guess word to evaluate.
        limit (float): Early termination limit for performance

    Returns:
        float: The maximum number of remaining words after the guess.
    """
    actual_limit = _max_word_score() if limit is None else limit
    if len(words) == 0:
        return actual_limit
    max_score = -1
    for w in words:
        temp_clue = Clues()
        temp_clue.add_clue(guess, get_clue_list(guess, w))
        this_score = temp_clue.filter_words_len(words)
        # Short ciruit if the score is too high already
        if this_score > actual_limit:
            return _max_word_score()
        # Find the maximum
        if this_score > max_score:
            max_score = this_score

    # Return the max number of resulting words, with a bias against words
    # that cannot be the correct answer
    return max_score  + (0 if guess in words else 0.1)
