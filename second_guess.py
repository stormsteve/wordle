# SPDX-FileCopyrightText: 2026 Steven M. Gale
# SPDX-License-Identifier: GPL-3.0-or-later

"""
The second guess in a game is special.
We can optimize performance by pre-computing the best second guess
given the starting word.
"""

import datetime                   # for now()
import logging                    # logging
import pathlib                    # cache file timestamp
import json                       # serializing the cache
from typing import Any, Optional  # typehinting with Any and Optional

from mytypes import WordSet       # My type hints
from config  import Config        # Wordle Solver Configuration
from clues   import Clues         # Clues gathered so far


class SecondGuess ():
    """
    Store one cached second-guess recommendation and its score.

    Instances of this class are serialized into the JSON cache used to speed
    up repeated second-guess lookups.
    """
    def __init__(self, guess:str, score:float) -> None:
        self._guess:str = guess
        self._score:float = score

    def __repr__(self) -> str:
        return json.dumps(self, default = SecondGuess.to_dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary for a singe guess and score."""
        if isinstance(self, SecondGuess):
            return {'guess':self._guess, 'score':self._score}
        raise TypeError(f'Unexpected type: {type(self).__name__}')

    def get_guess(self) -> str:
        """Get the guess string"""
        return self._guess

    def get_score(self) -> float:
        """Get the score for this guess"""
        return self._score


class SecondGuessCache ():
    """
    Manage the on-disk cache of optimized second-guess recommendations.

    The cache is keyed by the opening guess and resulting clue pattern so the
    solver can reuse previously computed second moves.
    """
    def __init__(self, dont_load:Optional[WordSet] = None) -> None:
        """
        dont_load:WordSet is a set of words not to load from the file
        """
        self._cache: dict[str, SecondGuess] = {}
        self._cache_stamp: float = 0.0
        self._dirty: bool = False
        self.load(dont_load)

    def load(self, dont_load:Optional[WordSet] = None) -> None:
        """Load the cache from a file if it is stale."""
        config = Config()
        cache_file_name = config.get_cache_file_name()

        # check if cache is stale
        try:
            cache_stamp = pathlib.Path(cache_file_name).stat().st_mtime
        except: # pylint: disable=bare-except
            # Ignore error and set timestamp to be the currect time
            cache_stamp = datetime.datetime.now().timestamp()

        if cache_stamp > self._cache_stamp:
            self._cache_stamp = cache_stamp
            # Deserialize (load) from a file
            logging.debug(
                'Loading cache file %s timestamp %s',
                cache_file_name,
                datetime.datetime.fromtimestamp(cache_stamp).strftime('%Y-%m-%d %H:%M:%S.%f'))
            try:
                with open(cache_file_name, 'r', encoding='UTF-8') as f:
                    cache_json = json.load(f)

                # This is a hack. I didn't make a custom function to read a
                # SecondGuess JSON
                word_length = config.get_word_length()
                self._cache.update({
                    k: SecondGuess(i['guess'], i['score'])
                    for k, i in cache_json.items()
                    if not dont_load or k[:word_length] not in dont_load
                })
#                for k, i in cache_json.items():
#                    if (not dont_load is None
#                        k[:config.get_word_length()] not in dont_load):
#                        self._cache[k] = SecondGuess(i['guess'], i['score'])

                logging.debug('Cache has %d entries', len(self._cache))
            except Exception as e: # pylint: disable=broad-exception-caught
                logging.debug('Could not load cache: %s', e)

    def to_json(self) -> str:
        """Custom method to serialize the cache dictionary to JSON."""
        # Convert SecondGuess objects to dictionaries using to_dict()
        serialized_cache = (
            {key: value.to_dict() for key, value in self._cache.items()})
        # Make it human readable
        return json.dumps(
            serialized_cache, sort_keys = True).replace('},', '},\n')

    def serialize(self) -> None:
        """Serialize the cache and write it to a file."""
        if self._dirty:
            self._dirty = False
            cache_file = pathlib.Path(Config().get_cache_file_name())
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_file, 'w', encoding='UTF-8') as f:
                f.write(self.to_json())
                f.write('\n')

    @staticmethod
    def key(clues:Clues) -> str:
        """Return the key used in the JSON format."""
        return f'{clues.get_guesses()[0]};{clues.get_last()}'

    def in_cache(self, clues: Clues) -> bool:
        """Is the given clue object in the cache?"""
        return SecondGuessCache.key(clues) in self._cache

    def in_cache2(self, start_clue:str) -> bool:
        """Is the given clue string in the cache?"""
        return start_clue in self._cache

    def get(self, clues: Clues) -> tuple[str, float]:
        """
        Get the best second guess for a given clue object. Also get the score.
        """
        return (
            self._cache[SecondGuessCache.key(clues)].get_guess(),
            self._cache[SecondGuessCache.key(clues)].get_score())

    def add(self, clues: Clues, guess: str, score: float) -> None:
        """Add a second guess clue to the cache."""
        if not self.in_cache(clues):
            self._dirty = True
            self._cache[SecondGuessCache.key(clues)] = SecondGuess(guess,score)

    def add2(self, start_clue:str, next_guess:str, score: float) -> None:
        """Add a second guess clue string to the cache."""
        if not self.in_cache2(start_clue):
            self._dirty = True
            self._cache[start_clue] = SecondGuess(next_guess, score)
