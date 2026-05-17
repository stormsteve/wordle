# SPDX-FileCopyrightText: 2026 Steven M. Gale
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Generate the clue list from a guess and answer.
"""

from __future__ import annotations
from mytypes import LetterList # My type hints
from config  import Config             # We need this for a configurable constant

def replace_first(letters: LetterList, letter: str, substitute: str) -> LetterList:
    """
    Replace the first occurrence of a given letter in a list with a substitute.

    This function modifies the input list in-place and returns it.

    Args:
        letters (LetterList): The list of letters to modify.
        letter (str): The letter to be replaced.
        substitute (str): The letter to replace with.

    Returns:
        LetterList: The modified list (same object as input).
    """
    for i, ltr in enumerate(letters):
        if ltr == letter:
            letters[i] = substitute
            break
    return letters

def get_clue_list(guess: str, ans: str) -> LetterList:
    """
    Generate the clue list from a guess and answer.

    Args:
        guess (str): The guess word.
        ans (str): The answer word.

    Returns:
        LetterList: List of 'g', 'y', 'b' for each position.
    """
    word_length = Config().get_word_length()
    answer_list = list(ans)
    color_list = [''] * word_length
    for i, letter in enumerate(guess):
        if letter == answer_list[i]:
            color_list[i] = 'g'
            # Replace green letters with the number '1' so they won't match twice
            answer_list[i] = '1'
    for i, letter in enumerate(guess):
        if color_list[i] != 'g' and letter in answer_list:
            color_list[i] = 'y'
            answer_list = replace_first(answer_list, letter, '1')
        elif color_list[i] != 'g':
            color_list[i] = 'b'
    return color_list
