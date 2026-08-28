# SPDX-FileCopyrightText: 2026 Steven M. Gale
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Load and filter the word lists used by the solver.

This module reads dictionary files, derives legal guess and answer sets, and
applies project-specific exclusions.
"""

# The filtering signature is retained for compatibility with existing callers.
# pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-boolean-expressions,unused-argument

import re                         # regex used for building the dict
import logging                    # logging
import sys                        # exit
import pathlib                    # bundled data paths

from mytypes import WordSet       # My type hints
from config  import Config        # Wordle Solver Configuration


def _resolve_word_file(filename: str) -> str:
    """Resolve a word-list path, including files bundled beside this module."""
    path = pathlib.Path(filename)
    if path.exists() or path.is_absolute():
        return str(path)

    bundled_path = pathlib.Path(__file__).resolve().parent / path
    return str(bundled_path) if bundled_path.exists() else filename

def load_word_set_from_file(filename: str) -> WordSet:
    """
    Load a set of words from a file, one word per line.

    Args:
        filename (str): The file to load words from.

    Returns:
        WordSet: The set of words.
    """
    words: WordSet = set()
    filename = _resolve_word_file(filename)
    try:
        with open(filename, 'r', encoding='UTF-8') as f:
            for line in f:
                word = line.rstrip()
                if word:
                    words.add(word)
    except FileNotFoundError:
        logging.error("File not found: %s", filename)
        sys.exit(1)
    return words

def extra_answers() -> WordSet:
    """Return legitimate words absent from the Ubuntu American word list."""
    return load_word_set_from_file('extra_answers.txt')

def rare_non_answers() -> WordSet:
    """
    Rare, legal, words that are non-answers and are either not in the standard
    Ubuntu linux American word list or are just not Wordle answers
    """
    return load_word_set_from_file('rare_non_answers.txt')

def not_words() -> WordSet:
    """Return non-words that somehow made it into our dictionary"""
    return {'assoc', 'bogon', 'contd', 'dding', 'gotta', 'illus', 'inced',
            'ioctl', 'kinda', 'lemme', 'lexer', 'multi', 'puter', 'pwned',
            'raith', 'smurf', 'sorta', 'stdio', 'sysop', 'thees', 'treas',
            'wanna', 'warez', 'xterm', 'zorch'}

def vulgar_words() -> WordSet:
    """Return vulgar or shaming words that can't be answers"""
    return load_word_set_from_file('vulgar.txt')

# Compile regular expressions
word_pattern = re.compile(r'^[a-z]+$')
roman_pattern = re.compile(r'^m{0,3}(cm|cd|d?c{0,3})?(xc|xl|l?x{0,3})?(ix|iv|v?i{0,3})?$')

def load_words_from_file(filename: str, word_length: int) -> tuple[WordSet, WordSet, WordSet]:
    """
    Loads words from a file and returns sets of words of specific lengths.

    Args:
        filename (str): The file to load words from.
        word_length (int): The length of words to consider.

    Returns:
        tuple[WordSet, WordSet, WordSet]: Sets of words of lengths
        `word_length`, `word_length - 1`, and `word_length - 2`.
    """
    legal_guesses: WordSet = set()
    one_char_less: WordSet = set()
    two_chars_less: WordSet = set()
    filename = _resolve_word_file(filename)

    try:
        with open(filename, 'r', encoding='UTF-8') as f:
            for line in f:
                word = line.rstrip()
                if word_pattern.match(word):
                    if len(word) == word_length:
                        legal_guesses.add(word)
                    elif len(word) == word_length - 1:
                        one_char_less.add(word)
                    elif len(word) == word_length - 2:
                        two_chars_less.add(word)
    except FileNotFoundError:
        logging.error("File not found: %s", filename)
        sys.exit(1)

    return legal_guesses, one_char_less, two_chars_less

def filter_legal_guesses(legal_guesses: WordSet, non_answers: WordSet,
                         vulgar: WordSet, word_length: int, one_char_less: WordSet,
                         two_chars_less: WordSet) -> tuple[WordSet, WordSet]:
    """
    Filters legal guesses and returns legal guesses and answers.

    Args:
        legal_guesses (WordSet): The set of legal guesses.
        non_answers (WordSet): The set of non-answers.
        vulgar (WordSet): The set of vulgar words.
        word_length (int): The length of words to consider.
        one_char_less (WordSet): The set of words one character less than `word_length`.
        two_chars_less (WordSet): The set of words two characters less than `word_length`.

    Returns:
        tuple[WordSet, WordSet]: The filtered legal guesses and answers.
    """
    roman_words = {word for word in legal_guesses if roman_pattern.match(word)}

    for word in list(legal_guesses): #Iterate on a copy to avoid modifying the set during iteration
        if word not in ('moped') and len(word) >= 3:
            # Filter out plurals and past tense (words ending in -s or -ed)
            if (word[:-1] in one_char_less and
                (word.endswith('s') and word[-2:] != 'ss' or word.endswith(('ed', 'es')))) or \
               (word[:-2] in two_chars_less and word.endswith(('ed', 'es'))):
                non_answers.add(word)

    legal_guesses.difference_update(roman_words)
    legal_guesses.difference_update(not_words())

#    with open('legal_guesses.txt','w',encoding='UTF-8') as f:
#        for word in sorted(legal_guesses):
#            f.write(word + '\n')

#    with open('legal_answers.txt','w',encoding='UTF-8') as f:
#        for word in sorted((legal_guesses - vulgar) - non_answers):
#            f.write(word + '\n')

    return legal_guesses, (legal_guesses - vulgar) - non_answers

def build_dictionaries() -> tuple[WordSet, WordSet]:
    """
    Builds two sets of words: one for legal guesses and the other for legal answers.

    Returns:
        tuple[WordSet, WordSet]: The sets of legal guesses and answers.
    """
    config = Config()
    word_length = config.get_word_length()
    filename = config.get_word_list_dictionary()

    legal_guesses, one_char_less, two_chars_less = load_words_from_file(filename, word_length)

    if word_length == 5:
        non_answers = rare_non_answers()
        legal_guesses.update(extra_answers())
        legal_guesses.update(non_answers)
    else:
        non_answers = set()

    vulgar = vulgar_words()

    return filter_legal_guesses(legal_guesses, non_answers, vulgar, word_length,
                                one_char_less, two_chars_less)
