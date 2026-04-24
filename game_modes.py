"""
Game mode classes for different Wordle game variants.
"""

from mytypes import WordSet, LetterList
from logic import Logic
from algorithm import accurate
from user_interface import input_guess


class Mode:
    """
    Base class for different game modes.

    Subclasses implement mode-specific behavior for guess display and input.
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
    Mode for advising the user on guesses while allowing custom input.
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
    Mode for solving based on user-provided clues.
    """

    @staticmethod
    def print_raw_guess(guess: str, row: int, logic: Logic) -> Logic:
        print(f'{str(row)} {guess.upper()} [{str(logic)}]')
        return logic


class ModePlay(Mode):
    """
    Mode for interactive play where the program selects the answer.
    """

    @staticmethod
    def get_user_guess(dictionary: WordSet, guess: str, words: WordSet,
                       clues, logic: Logic) -> str:
        return ModeAdvise.get_user_guess(dictionary, guess, words, clues, logic)