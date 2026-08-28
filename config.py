# SPDX-FileCopyrightText: 2026 Steven M. Gale
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Store shared runtime configuration for the Wordle solver.

This module exposes the singleton configuration object used by the CLI, GUI,
and solver logic.
"""

# The default algorithm is imported lazily to avoid a module import cycle.
# pylint: disable=import-outside-toplevel,attribute-defined-outside-init

from __future__ import annotations
import pathlib
from typing import Type, Callable

from mytypes import WordSet        # My type hints

class Config: # pylint: disable=too-many-instance-attributes,too-many-public-methods
    """
    Singleton container for runtime solver configuration.

    This holds command-line and application settings such as dictionary paths,
    word length, mode selection, caching, and algorithm choices.
    """
    _instance = None
    _default_function_initialized = False

    def __new__(cls: Type[Config]) -> Config:
        """Create the Config singleton."""
        if not cls._instance:
            cls._instance = super(Config, cls).__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize the Configuration Values."""
        # Only initialize once for the singleton
        if hasattr(self, '_mode'):
            return

        # List of first guesses when playing with 5-letter words
        # Already used by Wordle: {'saint', 'slate', 'trace', 'raise', 'crate'}
        self._first_guess_words = {'least', 'slant', 'roast', 'caret', 'sitar',
                                   'stare'}

        # How many possible words are needed to force us to run
        # child processes
        self._multi_processes_threshold = 10

        # Reduce the number of child processes when the CPU usage
        # passes this percentage
        self._max_cpu_percent = 90

        # The maximum word length.
        self._max_word_length = 19

        # The maximum guess "score" when searching for the best guess
        self._max_word_score = 9999

        # Cache file name
        self._cache_file_name = 'wordle_cache.json'
        self._cache_dir = '.'

        # word list dictionary. Can be set via the command line.
        self._word_list_dictionary: str = 'american-english'
        self._word_list_dictionary2: str = '/usr/share/dict/words'

        # The word length. Can be changed via the command line.
        self._word_length: int = 5

        # The maximum number of guesses. Can be changed via the
        # command line.
        self._max_guesses: int = 6

        # Maximum number of child processes to create for performance.
        self._max_child_processes: int = 0

        # Should we try to load second guesses from a cache file?
        self._use_cache: bool = False

        # The mode. Valid values are 'auto', 'clues', 'advise', and
        # 'play'. Can be changed via the command line.
        self._mode: str = ''

        # The starting word, or 'list'. Can be changed via the command line.
        self._start: str = ''

        # The answer, if known in advance. Can be set via the command line.
        self._answer: str = ''

    def set_word_list_dictionary(self, filename:str) -> None:
        """Set the word list dictionary."""
        self._word_list_dictionary = filename

    def set_word_list_dictionary2(self, filename:str) -> None:
        """Set the secondary word list dictionary."""
        self._word_list_dictionary2 = filename

    def set_word_length(self, length:int) -> None:
        """Set the word length."""
        self._word_length = length

    def set_max_guesses(self, limit:int) -> None:
        """Set the maximum number of guesses."""
        self._max_guesses = limit

    def set_max_child_processes(self, limit:int) -> None:
        """Set the maximum number of child processes."""
        self._max_child_processes = limit

    def set_use_cache(self, use:bool) -> None:
        """Set the flag to indicate if we use the word cache file."""
        self._use_cache = use

    def set_cache_dir(self, directory: str) -> None:
        """Set the directory containing the cache file."""
        self._cache_dir = directory

    def set_mode(self, mode:str) -> None:
        """Set the game play mode."""
        self._mode = mode

    def set_start(self, word:str) -> None:
        """Set the starting word."""
        self._start = word

    def set_answer(self, word:str) -> None:
        """Set the answer word."""
        self._answer = word

    def set_algorithm(self, func:Callable[[WordSet, str, float], float]) -> None:
        """Set the scoring algorithm."""
        self._default_function_initialized = True
        self._algorithm = func

    def get_word_list_dictionary(self) -> str:
        """Get the word list dictionary."""
        return self._word_list_dictionary

    def get_word_list_dictionary2(self) -> str:
        """Get the secondary word list dictionary."""
        return self._word_list_dictionary2

    def get_word_length(self) -> int:
        """Get the word length."""
        return self._word_length

    def get_max_guesses(self) -> int:
        """Get the maximum number of guesses."""
        return self._max_guesses

    def get_max_child_processes(self) -> int:
        """Get the maximum number of child processes."""
        return self._max_child_processes

    def get_use_cache(self) -> bool:
        """Get the flag to indicate if we use the word cache file."""
        return self._use_cache

    def get_mode(self) -> str:
        """Get the game play mode."""
        return self._mode

    def get_start(self) -> str:
        """Get the starting word."""
        return self._start

    def get_answer(self) -> str:
        """Get the answer word."""
        return self._answer

    def get_first_guess_words(self) -> WordSet:
        """Get the optimized list of starting words."""
        return self._first_guess_words

    def get_multi_processes_threshold(self) -> int:
        """Get the threshold of the number of child processes."""
        return self._multi_processes_threshold

    def get_max_cpu_percent(self) -> int:
        """Get the maximum CPU usage when running child processes."""
        return self._max_cpu_percent

    def get_max_word_length(self) -> int:
        """Get the maximum allowed word length."""
        return self._max_word_length

    def get_max_word_score(self) -> int:
        """Get the maximum word score."""
        return self._max_word_score

    def get_cache_file_name(self) -> str:
        """Get the complete path to the cache file."""
        return str(pathlib.Path(self._cache_dir) / self._cache_file_name)

    def get_algorithm(self) -> Callable[[WordSet, str, float], float]:
        """Get the scoring algorithm."""
        if not self._default_function_initialized:
            # Set the default scoring algorithm to use.
            from algorithm import accurate_avg # Functions for scoring guesses
            self._algorithm = accurate_avg
            self._default_function_initialized = True

        return self._algorithm
