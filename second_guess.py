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
import tempfile
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
        self._metadata: dict | None = None
        self.load(dont_load)

    def set_context(self, dictionary: WordSet, answers: WordSet) -> None: # pylint: disable=unused-argument
        """Set cache compatibility context, independent of source word-list contents."""
        config = Config()
        algorithm = config.get_algorithm()
        metadata = {
            'version': 3,
            'word_length': config.get_word_length(),
            'algorithm': f'{algorithm.__module__}.{algorithm.__qualname__}',
        }
        if self._metadata and not self._compatible_context(self._metadata, metadata):
            self._cache.clear()
            self._dirty = False
        self._metadata = metadata

    @staticmethod
    def _compatible_context(first: dict, second: dict) -> bool:
        """Compare settings that affect cache key shape or recommendation scoring."""
        return all(first.get(key) == second.get(key)
                   for key in ('version', 'word_length', 'algorithm'))

    def load(self, dont_load:Optional[WordSet] = None) -> None:
        """Load the cache from a file if it is stale."""
        config = Config()
        cache_file_name = config.get_cache_file_name()

        # check if cache is stale
        try:
            cache_stamp = pathlib.Path(cache_file_name).stat().st_mtime
        except OSError:
            return

        if cache_stamp > self._cache_stamp:
            # Deserialize (load) from a file
            logging.debug(
                'Loading cache file %s timestamp %s',
                cache_file_name,
                datetime.datetime.fromtimestamp(cache_stamp).strftime('%Y-%m-%d %H:%M:%S.%f'))
            try:
                with open(cache_file_name, 'r', encoding='UTF-8') as f:
                    cache_json = json.load(f)

                metadata = cache_json.get('metadata')
                if not isinstance(metadata, dict) or metadata.get('version') != 3:
                    logging.debug('Ignoring cache without compatible metadata.')
                    return
                if (self._metadata is not None
                        and not self._compatible_context(metadata, self._metadata)):
                    logging.debug('Ignoring cache with incompatible scoring settings.')
                    return
                self._metadata = metadata
                self._cache.update({
                    k: SecondGuess(i['guess'], i['score'])
                    for k, i in cache_json['entries'].items()
                    if not dont_load or k.split(';')[0] not in dont_load
                })
                self._cache_stamp = cache_stamp

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
            {'metadata': self._metadata, 'entries': serialized_cache},
            sort_keys = True).replace('},', '},\n')

    def serialize(self) -> None:
        """Publish a complete cache file atomically, preserving pending writes on failure."""
        if self._dirty:
            cache_file = pathlib.Path(Config().get_cache_file_name())
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(
                        mode='w', encoding='UTF-8', dir=cache_file.parent,
                        prefix=f'.{cache_file.name}.', suffix='.tmp', delete=False) as f:
                    temporary = pathlib.Path(f.name)
                    f.write(self.to_json())
                    f.write('\n')
                temporary.replace(cache_file)
                self._dirty = False
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)

    @staticmethod
    def key(clues:Clues) -> str:
        """Return the key used in the JSON format."""
        return f'{clues.get_guesses()[0]};{clues.get_last()}'

    def get_key(self, clues: Clues) -> str:
        """Return the short opening-word and feedback key."""
        return self.key(clues)

    def in_cache(self, clues: Clues) -> bool:
        """Is the given clue object in the cache?"""
        return self.get_key(clues) in self._cache

    def in_cache2(self, start_clue:str) -> bool:
        """Is the given clue string in the cache?"""
        return start_clue in self._cache

    def get(self, clues: Clues) -> tuple[str, float]:
        """
        Get the best second guess for a given clue object. Also get the score.
        """
        return (
            self._cache[self.get_key(clues)].get_guess(),
            self._cache[self.get_key(clues)].get_score())

    def add(self, clues: Clues, guess: str, score: float) -> None:
        """Add a second guess clue to the cache."""
        if not self.in_cache(clues):
            self._dirty = True
            self._cache[self.get_key(clues)] = SecondGuess(guess,score)

    def add2(self, start_clue:str, next_guess:str, score: float) -> None:
        """Add a second guess clue string to the cache."""
        if not self.in_cache2(start_clue):
            self._dirty = True
            self._cache[start_clue] = SecondGuess(next_guess, score)
