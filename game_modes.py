# SPDX-FileCopyrightText: 2026 Steven M. Gale
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Define the mode-specific hooks used by the Wordle game loop.

This module provides the mode classes that customize guess display, input
handling, and clue collection.
"""

# Mode implementations import UI/configuration helpers lazily to avoid cycles.
# pylint: disable=import-outside-toplevel

from mytypes import WordSet, LetterList
from logic import Logic
from algorithm import accurate
from user_interface import input_guess


class Mode:
    """
    Base interface for the solver's play and clue-entry modes.

    Subclasses override the small set of hooks that control how guesses are
    shown, how user input is collected, and where clue data comes from.
    """

    @staticmethod
    def print_raw_guess(guess: str, row: int, logic: Logic) -> Logic:
        """no-op"""
        # pylint: disable=unused-argument
        return logic

    @staticmethod
    def get_user_guess(dictionary: WordSet, guess: str, words: WordSet,
                       clues, logic: Logic) -> str:
        """no-op"""
        # pylint: disable=unused-argument
        return guess

    @staticmethod
    def get_clue(guess: str, ans: str) -> LetterList:
        """Get the clue from the user if we don't already know it."""
        from clue_list import get_clue_list
        from user_interface import get_user_clue
        return get_clue_list(guess, ans) if ans else get_user_clue()


class ModeAdvise(Mode):
    """
    Interactive helper mode that recommends a guess but accepts user input.
    """

    @staticmethod
    def print_raw_guess(guess: str, row: int, logic: Logic) -> Logic:
        print(f'{str(row)} Recommendation: {guess.upper()} [{str(logic)}]')
        return logic

    @staticmethod
    def get_user_guess(dictionary: WordSet, guess: str, words: WordSet,
                       clues, logic: Logic) -> str:
        from config import Config
        config = Config()
        start = config.get_start()
        user_guess = (start
                      if len(start) == config.get_word_length() and clues.get_num_guesses() == 0
                      else input_guess(dictionary))
        score = accurate(words, user_guess, config.get_max_word_score())
        logic.update('user input', score, words)
        import logging
        logging.info('guess=%s score=%s', user_guess, round(score, 3))
        return user_guess


class ModeClues(Mode):
    """
    Solver mode that displays guesses and expects clue feedback each round.
    """

    @staticmethod
    def print_raw_guess(guess: str, row: int, logic: Logic) -> Logic:
        print(f'{str(row)} {guess.upper()} [{str(logic)}]')
        return logic


class ModePlay(Mode):
    """
    Play mode for games where the application knows the answer internally.
    """

    @staticmethod
    def get_user_guess(dictionary: WordSet, guess: str, words: WordSet,
                       clues, logic: Logic) -> str:
        return ModeAdvise.get_user_guess(dictionary, guess, words, clues, logic)
