"""
Hold the knowledge gained from the clues.
"""

from typing import Iterator
from config import Config                          # Wordle Solver Configuration
from mytypes import WordSet, LetterSet, LetterList # My type hints


def _word_length() -> int:
    """Return the current configured word length."""
    return Config().get_word_length()


def _max_word_score() -> int:
    """Return the current configured max word score."""
    return Config().get_max_word_score()

class Yellows ():
    """
    Hold the yellow clues. There is a set of yellow letters for each
    of the possible letter positions.
    """
    def __init__(self) -> None:
        self._yellows: list[LetterSet] = [set() for _ in range(_word_length())]
        self._set_index = 0
        self._string_index = 0

    def __iter__(self) -> Iterator[str]:
        self._set_index = 0
        self._string_index = 0
        return self

    def __next__(self) -> str:
        while self._set_index < len(self._yellows):  # Outer loop for sets
            current_set = self._yellows[self._set_index]
            current_set_list = list(current_set)

            # Inner loop for strings
            while self._string_index < len(current_set_list):
                string_to_return: str = current_set_list[self._string_index]
                self._string_index += 1
                return string_to_return

            self._set_index += 1
            self._string_index = 0

        raise StopIteration  # No more sets or strings

    def __repr__(self) -> str:
        return f'{self._yellows=}'

    def index(self, i:int) -> LetterSet:
        """Return the set of letters at the given index"""
        return self._yellows[i]

    def merge(self, i:int, new:LetterSet) -> None:
        """Merge (union) new yellow letters into the given set"""
        self._yellows[i] = self._yellows[i] | new


class RequiredLetters ():
    """
    Keep a record of the letters required by a yellow clue. For each yellow letter found, we keep a
    tuple with the minimum and maximum number of times that the letter must appear in the answer.
    This is for handling cases with duplicate letters in the answer or duplicate letters in the
    guess.
    """
    def __init__(self) -> None:
        self._letter_map: dict[str, tuple[int,int]] = {}

    def __iter__(self) -> Iterator[str]:
        return iter(self._letter_map)

    def __repr__(self) -> str:
        return f'{self._letter_map=}'

    def get_min_max(self, letter:str) -> tuple[int, int]:
        """Get the minimum and maximum number of occurances for a letter"""
        return self._letter_map[letter]

    def add_yellow(self, letter:str, guess:LetterList, greens:LetterList, clue:LetterList) -> None:
        """Add a yellow letter that was found"""
        if letter not in self._letter_map:
            self._letter_map[letter] = (1, _word_length())
        (cur_min, cur_max) = self._letter_map[letter]
        num_letter = 0
        for i, guess_letter in enumerate(guess):
            if guess_letter == letter and (greens[i] == letter or clue[i] == 'y'):
                num_letter += 1
        self._letter_map[letter] = (max(cur_min, num_letter), cur_max)

    def add_black(self, letter:str, guess:LetterList, greens:LetterList, clue:LetterList) -> None:
        """After it was yellow or green we now have the same letter black"""
        if letter not in self._letter_map:
            self._letter_map[letter] = (1, _word_length())
        cur_min, _ = self._letter_map[letter]
        num_letter = 0
        for i, guess_letter in enumerate(guess):
            if guess_letter==letter and (greens[i]==letter or clue[i]=='y'):
                num_letter += 1
        self._letter_map[letter] = (cur_min, num_letter)


class Clues ():
    """
    Clues is a class to keep track of the guesses made and the resulting clues for those guesses.
    It holds a list of the guesses and all of the accumlulated clue information so far.

    The object can also filter a set of words based on the clues it holds.

    This is the work horse of the program, in terms of working within the games rules.

    Members:
        _blacks: set of letters not the the answer
        _greens: list of word_length positions, some might be letters
        _yellows: is a list of word_length positions, each a set letters
        _required: mapping of all of the known required letters to a touple with the minimum and
                   maximum number of required instances of that letter.
        _guesses: list of the guesses made so far
    """

    def __init__(self) -> None:
        self._blacks: LetterSet = set()
        self._greens = [''] * _word_length()
        self._yellows = Yellows()
        self._required = RequiredLetters()
        self._guesses: LetterList = []
        self._last_clue: LetterList = []

    def __repr__(self) -> str:
        return (f'{self._greens=} {self._yellows=} {self._blacks=} {self._required=} '
                f'{self._guesses=} {self._last_clue=}')

    def get_guesses(self) -> LetterList:
        """Return the list of guesses"""
        return self._guesses

    def get_num_guesses(self) -> int:
        """Return the number of guesses"""
        return len(self._guesses)

    def get_last(self) -> str:
        """Return the last clue"""
        return ''.join(self._last_clue)

    def is_possible_word(self, word: str) -> bool:
        """
        Checks whether the given word is a possible solution based on the current state of the
        Clues object. This is the bottle neck when it comes to performance so we short ciriut loops
        whenever possible.

        Args:
            word (str): The word to check.

        Returns:
            bool: True if the word is a possible solution, False otherwise.
        """

        # Initialize a dictionary to store the count of each letter in the word
        word_letter_counts: dict[str, int] = {}

        # Loop over the word once
        for i, letter in enumerate(word):
            # Check for black letters
            if letter in self._blacks:
                return False

            # Check for mismatched green letters
            if self._greens[i] and letter != self._greens[i]:
                return False

            # Check for yellow letters in yellow positions
            if letter in self._yellows.index(i):
                return False

            # Increment the count of the current letter
            word_letter_counts[letter] = word_letter_counts.get(letter, 0) + 1

        # Check required letter counts
        for letter in self._required:
            actual_count = word_letter_counts.get(letter, 0)
            min_count, max_count = self._required.get_min_max(letter)
            if not min_count <= actual_count <= max_count:
                return False

        # If none of the above conditions were met, the word is a possible solution
        return True

    def is_possible_word_old(self, word: str) -> bool:
        """
        Checks whether the given word is a possible solution based on the current state of the Clues
        object. This is the bottle neck when it comes to performance so we short ciriut loops
        whenever possible.

        Args:
            word (str): The word to check.

        Returns:
            bool: True if the word is a possible solution, False otherwise.
        """

        # Filter out all words that contain black letters
        for letter in word:
            if letter in self._blacks:
                # If a black letter is found, immediately return False
                return False

        # Filter out words that are missing any green letters
        for letter, green in zip(word, self._greens):
            if green and letter != green:
                # If a mismatched green letter is found, immediately return False
                return False

        # Filter out words with yellow letters in a yellow place
        for i, letter in enumerate(word):
            if letter in self._yellows.index(i):
                # If a yellow letter appears in a yellow position, immediately return False
                return False

        # Make sure that any known yellows actually appear the right number of times in the word
        for letter in self._required:
            min_count, max_count = self._required.get_min_max(letter)
            actual_count = word.count(letter)
            if not min_count <= actual_count <= max_count:
                # If the word doesn't meet the required letter count, immediately return False
                return False

        # If none of the above conditions were met, the word is a possible solution
        return True

    def filter_words(self, words:WordSet, limit:float | None = None) -> WordSet:
        """
        Filter a set of words and return a new set of the matching words. If the result would have
        more than "limit" words, return the set {'limit_reached'}. This is a performance
        optimization.
        """
        actual_limit = _max_word_score() if limit is None else limit
        filtered_words = set()
        for word in words:
            if self.is_possible_word(word):
                # Add the word to the filtered word set
                filtered_words.add(word)
                # Short circuit the loop and return a special set if we've reached the limit
                if len(filtered_words) > actual_limit:
                    return {'limit_reached'}

        return filtered_words

    def filter_words_len(self, words:WordSet, limit:float | None = None) -> int:
        """Return the length of the filtered list."""
        filtered_set = self.filter_words(words, limit)
        return (
            len(filtered_set)
            if len(filtered_set) != 1 or 'limit_reached' not in filtered_set
            else _max_word_score())

    def _add_clue_green(self, guess_list:LetterList, clue_list:LetterList) -> None:
        """
        Find the green letters. Used to remove the old yellows too but that was a bug.
        """
        for i, letter in enumerate(guess_list):
            if clue_list[i] == 'g':
                self._greens[i] = letter

    def _add_clue_yellow_black(self,guess_list:LetterList, clue_list:LetterList) -> list[LetterSet]:
        """Find the yellows and blacks."""

        new_yellows:list[LetterSet] = \
            [set() for _ in range(_word_length())]

        for i, letter in enumerate(guess_list):
            if clue_list[i] == 'y':
                new_yellows[i].add(letter)
                self._required.add_yellow(letter, guess_list, self._greens, clue_list)
            elif letter != self._greens[i]:
                if (letter in self._greens or letter in self._required):
                    self._required.add_black(letter, guess_list, self._greens, clue_list)
                else:
                    self._blacks.add(letter)
        return new_yellows

    def add_clue(self, guess:str, clue_list:LetterList) -> None:
        """Add a new clue to the history of clues"""

        self._guesses.append(guess)
        self._last_clue = clue_list

        # Limit guess_list to word_length just in case we got a long guess
        guess_list = list(guess[:_word_length()])

        # Handle the green letters.
        self._add_clue_green(guess_list, clue_list)

        # Find the yellows and handle the black ones.
        new_yellows= self._add_clue_yellow_black(guess_list, clue_list)
        # Merge the new_yellows with the existing yellows
        for i, yellow_pos in enumerate(new_yellows):
            self._yellows.merge(i, yellow_pos)
