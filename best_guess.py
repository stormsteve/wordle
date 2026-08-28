# SPDX-FileCopyrightText: 2026 Steven M. Gale
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Choose the next guess from the current candidate sets.

This module combines scoring, cache lookups, and answer filtering to select
the most useful next Wordle guess.
"""

# Late imports below are intentional because this flat module layout has
# circular dependencies between configuration, clues, and guess selection.
# pylint: disable=import-outside-toplevel,reimported,redefined-outer-name,wrong-import-order,comparison-with-callable,too-many-locals

from mytypes import WordSet
from myconcurrent import process_accurate_logic
from logic import Logic
from second_guess import SecondGuessCache
from dictionary import vulgar_words
import logging


def _log_a_score(results: list[str], scores: dict[str, float], idx: int) -> None:
    """
    Show the Nth best guess if logging is on
    """
    if len(results) > idx:
        logging.info('accurate score for %s: %s', results[idx], round(scores[results[idx]], 3))


def _log_a_few_scores(results: list[str], scores: dict[str, float]) -> None:
    """
    Show the best guesses if logging is on
    """
    if len(results) == 0:
        return

    # Get the lowest value
    lowest_value = scores[results[0]]

    # Find the index of the first value that's different from lowest_value
    num_to_log = len(results) - 1
    for i, result in enumerate(results):
        if scores[result] > lowest_value:
            num_to_log = i
            break

    # Log all entries with the lowest value plus the next entry (if it exists) in reverse order
    if num_to_log > 10:
        logging.info('accurate score %d words', num_to_log - 1)
        num_to_log = 10

    for i in range(num_to_log, -1, -1):
        _log_a_score(results, scores, i)


def log_solution_space(words: WordSet) -> None:
    """
    Log information about the current solution space.
    """
    import logging
    if len(words) < 10:
        logging.info('Solution space is %d word%s=%s',
                     len(words),
                     's' if len(words) > 1 else '',
                     words)
    else:
        logging.info('Solution space is %d words', len(words))
        logging.debug('words=%s', words)


def get_cached_guess(clues, words: WordSet):
    """
    Attempt to retrieve a cached guess for the second guess optimization.

    Returns the cached guess and logic if available, otherwise None.
    """
    from config import Config
    config = Config()
    if config.get_use_cache() and clues.get_num_guesses() == 1:
        guess_cache = SecondGuessCache()
        if guess_cache.in_cache(clues):
            (guess, score) = guess_cache.get(clues)
            logic = Logic()
            logic.update('cache lookup', float(score), words)
            return (guess, logic)
    return None


def select_guess_set(dictionary: WordSet, words: WordSet, clues) -> WordSet:
    """
    Select the set of guesses to evaluate based on remaining possibilities and guesses.
    If there are 3 or less possible answers or if it's our last guess then pick an answer from
    the possible answer set. Otherwise we might want to pick a guess from some known non-answers
    because they might better narrow down the soluiton. But don't use vulgar words.
    """
    from config import Config
    config = Config()
    return (words
            if len(words) < 3 or clues.get_num_guesses() > config.get_max_guesses() - 2
            else dictionary - vulgar_words())


def find_best_guess(all_guesses: WordSet, words: WordSet) -> tuple[list[str], float]:
    """
    Evaluate all guesses and return all guesses with the minimum score and that score.
    """
    from config import Config
    config = Config()
    scores = process_accurate_logic(all_guesses, words)
    if not scores:
        return [], config.get_max_word_score()
    min_score = min(scores.values())
    best_guesses = [guess for guess, score in scores.items() if score == min_score]
    results = sorted(scores, key=scores.__getitem__)
    _log_a_few_scores(results, scores)
    return best_guesses, min_score


def resolve_guess_ties(best_guesses: list[str], words: WordSet) -> str:
    """
    Resolve ties between equally-scored guesses using meta-scoring with alternate algorithms.
    """
    from config import Config
    from algorithm import accurate_avg, accurate_median, accurate_max

    config = Config()
    current_alg = config.get_algorithm()
    other_algs = [alg for alg in [accurate_avg, accurate_median, accurate_max]
                  if alg != current_alg]
    meta_scores = {}
    for guess in best_guesses:
        scores = [alg(words, guess, config.get_max_word_score()) for alg in other_algs]
        meta_scores[guess] = sum(scores)
    min_meta = min(meta_scores.values())
    final_candidates = [g for g in best_guesses if meta_scores[g] == min_meta]
    if len(final_candidates) != len(best_guesses):
        import logging
        logging.info('tie-breaking meta_scores: %s',
                     {k: round(v, 3) for k, v in
                      sorted(meta_scores.items(), key=lambda item: item[1])})
    import random
    return random.choice(final_candidates)


def best_guess(dictionary: WordSet, words: WordSet, clues) -> tuple[str, Logic]:
    """
    Determine the optimal guess from the current word set.

    Uses caching for second guesses if enabled. Selects from all guesses or only answers
    depending on remaining attempts.

    Args:
        dictionary (WordSet): Full set of legal guesses.
        words (WordSet): Current possible answers.
        clues: Accumulated clues so far.

    Returns:
        tuple[str, Logic]: The best guess and its logic information.
    """
    from config import Config
    config = Config()
    logic = Logic()
    if not words:
        logic.update('unknown word', 0, set())
        return ('unknown word'[0:config.get_word_length()], logic)  # No solution

    log_solution_space(words)

    cached = get_cached_guess(clues, words)
    if cached:
        return cached

    all_guesses = select_guess_set(dictionary, words, clues)
    best_guesses, score = find_best_guess(all_guesses, words)

    if not best_guesses:
        result = 'unknown word'[0:config.get_word_length()]
    elif len(best_guesses) == 1:
        result = best_guesses[0]
    else:
        result = resolve_guess_ties(best_guesses, words)
    logic.update('accurate', score, words)
    return (result, logic)
