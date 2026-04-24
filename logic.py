"""
    Logic is a class to keep track of the logic used for a particular guess.
"""

from mytypes import WordSet       # My type hints


class Logic:
    """
    Logic is a class to keep track of the logic used for a particular guess. It
    holds the name of the logic, the evaluated score of the word chosen, and
    the list of possible words it chose from.

    This object is constructed when choosing a guess word so that we can
    display the logic used to the end-user.
    """

    def __init__(self) -> None:
        self._name: str = ''
        self._score: float = 0.0
        self._words: WordSet = set()

    def __str__(self) -> str:
        length = len(self._words)
        res =  f'{self._name} score={self._score:.2f}, len={length}'.format()
        if 0 < length < 10:
            res += f' {self._words.__str__()}'
        return res

    def update(self, name: str, score: float, words: WordSet) -> None:
        """
        Add a logic step to the history.

        Parameters:
            name (str): The logical step method used
            score (float): The score (average word list length after this step)
            words (WordSet): The possible legal answers before the step
        """
        self._name = name
        self._score = score
        self._words = words.copy()

    def get_score(self) -> float:
        """
        Return the score value.
        """
        return self._score
