#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Steven M. Gale
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Build and refresh the second-guess cache for the Wordle solver.

This batch utility precomputes cached second guesses and summarizes starting
word performance across the answer set.
"""

from __future__ import annotations     # For Queue type annotations

from multiprocessing import Process, Queue
import queue                           # for queue.Empty
import time
import datetime
import os                              # For terminal width
from sys import modules                # For cProfile check

import psutil                          # For CPU information

from myconcurrent import Concurrent    # child process and queue help
from mytypes import WordSet            # My type hints
from config import Config              # Wordle Solver Configuration
from logic  import Logic               # Logic Used for a Guess
from clues  import Clues               # Clues gathered so far
from clue_list import get_clue_list    # To generate a clue list
from second_guess import SecondGuessCache # Optimize 2nd guess
from dictionary import build_dictionaries
from algorithm import accurate_max, accurate_median, accurate_avg
from best_guess import best_guess

config = Config()
config.set_max_guesses(6)
config.set_algorithm(accurate_avg)

cpus = psutil.Process().cpu_affinity() # cpu list

# If cProfile is active then act like we only have 1 CPU
if cpus is None or 'profile' in modules:
    cpus = []

NUM_JOBS = len(cpus)

config.set_max_child_processes(0) # we do the process control, not wordle.py

START_TIME = datetime.datetime.now()
(legal_guesses, legal_answers) = build_dictionaries()

num_answers = len(legal_answers)

first_guess_words = {
    'salet', 'caret', 'crate', 'trace', 'roast', 'crane', 'slate', 'slant',
    'trice', 'least', 'stare', 'train', 'saint', 'react', 'stole', 'snare',
    'saner', 'sitar', 'stile', 'cater', 'stale', 'slier', 'slice', 'stair',
    'rinse', 'close', 'scale', 'sonar', 'raise', 'scare', 'roate', 'arose',
    'trail', 'store', 'trade', 'parse', 'trial', 'caste', 'taser', 'soare',
    'tares', 'alien', 'orate', 'salon', 'learn', 'toner', 'irate', 'alert',
    'dealt', 'snort', 'cleat', 'snore', 'coast', 'since', 'tonal', 'crest',
    'aline', 'siren', 'alter', 'stain', 'stone', 'renal', 'aisle', 'score',
    'tries', 'later', 'torsi', 'tenor', 'liner', 'snarl', 'solar', 'laden',
    'tread', 'trend', 'snide', 'risen', 'snail', 'arson', 'canoe', 'steal',
    'snarl', 'renal', 'aster', 'astir', 'stein', 'rosin', 'oaten', 'aisle',
    'laser', 'arson', 'triad', 'torsi', 'cadet', 'snide', 'noise', 'inset',
    'actor', 'stern', 'recta', 'stand', 'islet', 'inlet', 'resin', 'inert',
    'sedan', 'adorn', 'crisp', 'onset', 'anise', 'tidal', 'staid', 'olden',
    'ratio', 'intel', 'radio', 'enrol', 'louse', 'older', 'stead', 'ascot',
    'oldie', 'stoic', 'osier', 'antic', 'aside', 'ocean', 'intro', 'ideal',
    'louie', 'media', 'about', 'adieu', 'audio'}

# salet:3.43 caret:3.44 crate:3.44 trace:3.44 roast:3.45 crane:3.45 slate:3.45 slant:3.45
# trice:3.46 least:3.46 stare:3.46 train:3.46 saint:3.46 react:3.46 stole:3.46 snare:3.46
# saner:3.47 sitar:3.47 stile:3.47 cater:3.47 stale:3.47 slier:3.47 slice:3.47 stair:3.47
# rinse:3.47 close:3.47 scale:3.47 sonar:3.48 raise:3.48 scare:3.48 roate:3.48 arose:3.48
# trail:3.48 store:3.48 trade:3.48 parse:3.48 trial:3.48 caste:3.48 taser:3.48 soare:3.49
# tares:3.49 alien:3.49 orate:3.49 salon:3.49 learn:3.49 toner:3.49 irate:3.49 alert:3.49
# dealt:3.49 snort:3.49 cleat:3.49 snore:3.49 coast:3.49 since:3.49 arise:3.49 snail:3.50
# canoe:3.50 score:3.50 solar:3.50 tread:3.50 laden:3.50 tries:3.50 later:3.50 scent:3.50
# tenor:3.50 niter:3.50 tonal:3.50 crest:3.50 aline:3.50 siren:3.50 alter:3.50 stain:3.51
# stone:3.51 rouse:3.51 trend:3.51 liter:3.51 risen:3.51 salty:3.51 liner:3.51 atone:3.51
# steal:3.51 snarl:3.51 renal:3.51 aster:3.51 astir:3.51 stein:3.52 rosin:3.52 oaten:3.52
# aisle:3.52 laser:3.52 arson:3.52 triad:3.52 torsi:3.52 cadet:3.52 snide:3.52 noise:3.52
# inset:3.52 actor:3.53 stern:3.53 recta:3.53 stand:3.53 islet:3.53 inlet:3.53 resin:3.53
# inert:3.53 sedan:3.53 adorn:3.54 crisp:3.54 onset:3.54 anise:3.54 tidal:3.54 staid:3.54
# olden:3.54 ratio:3.54 intel:3.54 radio:3.55 enrol:3.55 louse:3.55 older:3.55 stead:3.56
# ascot:3.56 oldie:3.56 stoic:3.57 osier:3.57 antic:3.57 aside:3.58 ocean:3.58 intro:3.58
# ideal:3.58 louie:3.59 media:3.60 about:3.62 adieu:3.64 audio:3.66

first_guess_words = {
    'anise', 'stand', 'astir', 'rosin', 'oaten', 'aster', 'stern', 'inlet',
    'inert', 'oldie', 'stein', 'recta', 'resin', 'older', 'actor', 'sedan',
    'islet', 'enrol', 'olden', 'staid', 'tidal', 'intel', 'ratio', 'antic',
    'stoic', 'ascot', 'osier', 'radio', 'stead', 'louie', 'louse', 'intro',
    'ocean', 'ideal', 'aside', 'media', 'about', 'adieu', 'audio'
     }

# first_guess_words = {'crate'}


class GuessCache (SecondGuessCache):
    """
    Extend SecondGuessCache with cache-building workflow support.

    In addition to cached lookups, this class computes missing best second
    guesses and notifies the parent process when new cache entries are ready to
    persist.
    """

    def cached_best_guess(
            self, legal_guess_list: WordSet, words:WordSet, clues: Clues,
            out_queue:Queue[str] # pylint: disable=unsubscriptable-object
            ) -> tuple[str, WordSet]:
        """
        Find the best guess, taking into account that the best 2nd guess might
        already be in the cache. Signal the boss if we updated the cache.
        """
        words = clues.filter_words(words)
        guesses = clues.get_num_guesses()

        # If we need a 2nd guess and it is already in the cache, then
        # just use that and return.
        if guesses == 1 and self.in_cache(clues):
            logic = Logic()
            score = self._cache[self.key(clues)].get_score()
            logic.update('cached guess', score, set())
            return self._cache[self.key(clues)].get_guess(), words

        # Find the best guess
        this_guess, logic = best_guess(legal_guess_list, words, clues)

        # If we just found the 2nd guess then add it to the cache and
        # update daddy
        if guesses == 1 and not self.in_cache(clues):
            score = round(logic.get_score(), 3)
            self.add(clues, this_guess, score)
            out_queue.put(f'CACHE_UPDATE:{self.key(clues)}:{this_guess}:{score}')

        return this_guess, words


# Loop over the answers
def process_answers(in_queue:Queue[str],out_queue:Queue[str],#pylint:disable=unsubscriptable-object
                    cache: GuessCache, progress:bool = False) -> bool:
    """
    The child process. It picks up an answer word from the input queue and
    finds the best guess to solve for that word. It then send the results
    to the the master process via the output queue.
    """
    max_guesses = config.get_max_guesses()
    while True:
        try:
            answer = in_queue.get(block=True, timeout=0.3)
            cache.load()
            # Solve for each starting word
            for first_guess in first_guess_words:
                clues = Clues()
                words = legal_answers.copy()
                guess = first_guess
                for row_num in range(1, max_guesses + 1):
                    clues.add_clue(guess, get_clue_list(guess, answer))
                    if guess == answer:
                        break
                    if row_num == max_guesses:
                        print(f'\n{first_guess=} {answer=} guesses='
                              f'{clues.get_guesses()} {words=} {clues=}')
                        break
                    guess, words = cache.cached_best_guess(legal_guesses, words, clues, out_queue)
                out_queue.put(f'{first_guess}:{row_num}:{answer}:0')
                if progress:
                    print(f'\r{answer=}: {first_guess=}', end='', flush=True)

        except queue.Empty: # pylint: disable=duplicate-code
            break
        except KeyboardInterrupt:
            return False
    return True

def print_scores(score:dict[str, int], count:dict[str, int], max_num: int = 99999) -> None:
    """
    Display our progress
    """
    normalized = {}
    total_guesses = 0
    total_count = 0
    if max_num == -1:
        columns, _ = os.get_terminal_size()
        max_num = max(int((columns - 49) / 11), 0)
    for (s, c) in score.items():
        normalized[s] = int(100 * c / count[s]) / 100 if count[s] else 0
        total_guesses += c
        total_count += count[s]
    results=sorted(normalized, key=normalized.__getitem__)
    for j, i in enumerate(results):
        if j < max_num:
            print(f'{i}:{normalized[i]:.2f} ', end='', flush=True)
    print(f'Overall:{(total_guesses/total_count):.3f} '.format(),
          end='', flush=True)

def fill_and_run(answers:set[str], concurrent:Concurrent, cache:GuessCache) -> None:
    """Fill the outqueue with work to do. Process and fill the inqueue with the results"""

    # Loop over the dictionary and queue it up
    for answer in sorted(answers):
        concurrent.get_outqueue().put(answer)

    inqueue = concurrent.get_inqueue()
    outqueue = concurrent.get_outqueue()

    # Launch the child processes or do the work in a this thread. Don't launch
    # child processes if there aren't extra CPUs
    if NUM_JOBS > 0:
        for _ in range(NUM_JOBS):
            p = Process(target=process_answers, args=(outqueue, inqueue, cache))
            concurrent.add_process(p)
            time.sleep(0.05)
            p.start()
        return

    # Single threaded
    process_answers(outqueue, inqueue, cache, True)
    return

def seconds_to_time(seconds:int) -> tuple[int, int, int]:
    """Convert seconds into hours, minutes, and seconds"""
    hr  = int(seconds / 3600)
    mi  = int((seconds - hr * 3600) / 60)
    sec = int(seconds - hr * 3600 - mi * 60)
    return hr, mi, sec

def print_status( # pylint: disable=too-many-arguments,too-many-positional-arguments
        last_print_time:int,
        running_total:int,
        num_alive:int, answer:str,
        score:dict[str, int], count:dict[str, int]) -> int:
    """Print the status update if more than 1 second passed."""
    rt = datetime.datetime.now() - START_TIME
    if int(rt.seconds) > last_print_time:
        last_print_time = int(rt.seconds)
        seconds_left = ((num_answers * len(first_guess_words) - running_total)
                        / (running_total / rt.seconds))
        hr, mi, sec = seconds_to_time(rt.seconds)
        print(f'\r{hr:0>2}:{mi:0>2}:{sec:0>2} '.format(), end='', flush=True)
        hr, mi, sec = seconds_to_time(int(seconds_left))
        print(f'{hr:0>2}:{mi:0>2}:{sec:0>2} {num_alive} {answer} '
              f'{100 * running_total / num_answers / len(first_guess_words):.2f}% '.format(),
              end='', flush=True)
        print_scores(score, count, -1)
    return last_print_time

def read_results(concurrent: Concurrent, cache:GuessCache) -> tuple[dict[str, int], dict[str, int]]:
    """Read the results from the queue and write the cache file"""

    score : dict[str, int] = {}
    count : dict[str, int] = {}
    running_total = 0
    running_score = 0
    last_print_time = 0
    cache_update_count = 0
    num_alive = concurrent.get_num_alive()

    while True:
        try:
            result = concurrent.get_inqueue().get(block=True, timeout=0.3)
        except queue.Empty:
            num_alive = concurrent.get_num_alive()
            if not concurrent.is_child_abnormal_exit() and num_alive:
                continue
            break
        else:
            (guess, rows, answer, score_text) = result.split(':')
            if guess == 'CACHE_UPDATE':
                if not cache.in_cache2(rows):
                    cache.add2(rows, answer, float(score_text))
                    cache_update_count += 1
                    if cache_update_count > 3:
                        cache.serialize()
                        cache_update_count = 0
                continue
            if guess in score:
                score[guess] += int(rows)
                count[guess] += 1
            else:
                score[guess]  = int(rows)
                count[guess]  = 1
            running_total += 1
            running_score += int(rows)
            last_print_time = print_status(last_print_time, running_total,
                                           num_alive, answer, score, count)
    return score, count


def main() -> None:
    """Here is the main code."""

    score : dict[str, int] = {}
    count : dict[str, int] = {}

    print('First guess words:', first_guess_words)

    concurrent = Concurrent()
    cache = GuessCache(first_guess_words)

    try:
        fill_and_run(legal_answers, concurrent, cache)

        score, count = read_results(concurrent, cache)

        cache.serialize()

    except KeyboardInterrupt:
        print('\n')
        concurrent.clean_up_dirty(1)

    print('\n')

    if concurrent.is_child_abnormal_exit():
        concurrent.clean_up_dirty(2)

    concurrent.join_processes()

    print('\nFinal results:')
    print(f'Checked {len(first_guess_words)} starting words against '
          f'{num_answers} answers.')
    print_scores(score, count)
    print('')


if __name__ == '__main__':
    main()
else:
    print('Not intended to be an imported module.')
