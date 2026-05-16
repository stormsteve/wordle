# SPDX-FileCopyrightText: 2026 Steve Gale <galesteven@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

"""
User interface functions for Wordle game input/output handling.
"""

from mytypes import WordSet, LetterList
from clue_list import get_clue_list
from colorama import Back, Style


def input_lower() -> str:
    """
    Read user input, convert to lowercase, and strip whitespace.

    Exits on error.

    Returns:
        str: The processed input string.
    """
    try:
        return str(input()).lower().strip()
    except: # pylint: disable=bare-except
        import sys
        sys.exit(1)


def validate_guess_input(guess: str, dictionary: WordSet, logger, last_guess: str) -> tuple[bool, str]:
    """
    Validate a guess input and return validation result and updated last_guess.
    """
    from config import Config
    config = Config()
    if len(guess) != config.get_word_length():
        import logging
        logging.error('%s is does not have %d letters.', guess, config.get_word_length())
        return False, last_guess
    if (guess in dictionary or
         logger.getEffectiveLevel() == 10 or  # logging.DEBUG
         last_guess == guess):
        return True, last_guess
    else:
        import logging
        logging.error('%s is not a valid word. Repeat it to force acceptance.', guess)
        return False, guess


def input_guess(dictionary: WordSet) -> str:
    """
    Prompt user for a guess and validate it against the dictionary.

    Allows forcing invalid words in debug mode or by repeating.

    Args:
        dictionary (WordSet): Legal words.

    Returns:
        str: The validated guess.
    """
    import logging
    logger = logging.getLogger()
    last_guess = ''
    while True:
        print('Guess> ', end = '')
        guess = input_lower()
        valid, last_guess = validate_guess_input(guess, dictionary, logger, last_guess)
        if valid:
            break
    return guess


def is_only_clue_letters(user_clue: str) -> bool:
    """
    Check if the clue string contains only valid clue characters.

    Args:
        user_clue (str): The clue string to validate.

    Returns:
        bool: True if only 'g', 'y', 'b' are present.
    """
    return all(letter in {'g', 'y', 'b'} for letter in user_clue)


def get_user_clue() -> LetterList:
    """
    Prompt user for a clue and validate it.

    Returns:
        LetterList: The clue as a list of characters.
    """
    while True:
        print('Clue [gyb]> ', end = '')
        manual = input_lower()
        from config import Config
        config = Config()
        if len(manual) != config.get_word_length():
            import logging
            logging.error('Clue must be %d letters long.', config.get_word_length())
        elif not is_only_clue_letters(manual):
            import logging
            logging.error('Clue must only contain g, y, and b.')
        else:
            break

    return list(manual)


def display_row(num: int, clue_list: LetterList, guess: str, logic: str = '') -> None:
    """
    Display a single guess row with colors.

    Args:
        num (int): Row number.
        clue_list (LetterList): Clue colors.
        guess (str): The guess word.
        logic (str): Optional logic information.
    """
    # Limit to word_length just in case we got a longer guess
    from config import Config
    config = Config()
    word_length = config.get_word_length()
    guess_list = list(guess[:word_length])
    color_list = [''] * word_length
    color_map = {'g': Back.GREEN, 'y': Back.YELLOW, 'b': Back.BLACK}
    for i in range(len(guess_list)):
        color_list[i] = color_map[clue_list[i]]
    print(f'{str(num)} ', end = '')
    for letter, color in zip(guess, color_list):
        print(color + letter.upper(), end = '')
    print(Style.RESET_ALL, end = '')
    if logic:
        print(f' [{logic}]')
    else:
        print()


def display_board(clues, ans: str) -> None:
    """
    Display the full game board with all guesses.

    Args:
        clues: The clues object.
        ans (str): The answer word.
    """
    for i, guess in enumerate(clues.get_guesses()):
        display_row(i+1, get_clue_list(guess, ans), guess)
