#!/usr/bin/env python3

"""
Wordle Solver

A Python program to solve NYT Wordle puzzles using optimal guessing strategies.
Supports multiple modes including automatic solving, clue-based solving, advice mode, and interactive play.
"""

from __future__ import annotations     # for forward reference of Clues type

# for running slow algorithms with multiple processes
from multiprocessing import Process
import queue                      # for queue.Empty
import random                     # For picking a random word
import sys                        # argv[]
import logging                    # logging
import argparse                   # command line parsing
import pathlib                    # dictionary file check

import psutil                     # CPU information
from colorama import Back, Style  # color text output

from mytypes import WordSet, LetterList   # My type hints
from config  import Config                # Wordle Solver Configuration
from logic   import Logic                 # Logic Used for a Guess
from clues   import Clues                 # Clues gathered so far
from clue_list import get_clue_list       # To generate a clue list
from algorithm import accurate, accurate_avg, accurate_max, accurate_median # Algorithm to score guesses
from second_guess import SecondGuessCache # Optimize 2nd guess
from dictionary import build_dictionaries, vulgar_words # Load dictionaries
from myconcurrent import Concurrent       # Child process and queue help

config = Config() # Load the configuration into a singleton

MAX_CPU_PERCENT = config.get_max_cpu_percent()
MAX_WORD_LENGTH = config.get_max_word_length()
FIRST_GUESS_WORDS = config.get_first_guess_words()
MAX_WORD_SCORE = config.get_max_word_score()


def random_word(words: WordSet) -> str:
    """
    Select and return a random word from the given set of words.

    Args:
        words (WordSet): A set of words to choose from.

    Returns:
        str: A randomly selected word.
    """
    return random.choice(list(words))


def is_cpu_too_busy() -> bool:
    """
    Check if the CPU is too busy and child processes should exit.

    Returns:
        bool: True if CPU usage is high and processes should stop.
    """
    # Check the CPU usage since the last call. This is relatively fast
    if psutil.cpu_percent() > MAX_CPU_PERCENT:
        # The load is high, so next we check if it is still high and not going down (maybe a
        # different process detected the high load and exited). This call takes time, and our
        # current process will sleep. We'll compute the average CPU usage for all of the other
        # processes.
        cpu_list = psutil.cpu_percent(interval=0.2, percpu=True)
        return not sum(cpu_list)/float(len(cpu_list)) > MAX_CPU_PERCENT
    return False

def get_guess_score(conc:Concurrent, words: WordSet, pid: int) -> bool:
    """
    Child process function to compute and score guesses.

    Processes guesses from the input queue, calculates their scores, and sends results to output queue.
    Exits if CPU load is too high.

    Args:
        conc (Concurrent): The concurrent processing object for queues.
        words (WordSet): The set of possible answers.
        pid (int): Process ID for load checking.

    Returns:
        bool: True if process completed successfully.
    """
    min_score = MAX_WORD_SCORE
    psutil.cpu_percent() # First call always returns 0.0, so ignore the result
    while True:
        try:
            guess = conc.get_outqueue().get(block = True, timeout = 0.25)
            score = accurate(words, guess, min_score)
            # Send our new lowest-score guess to the master. Include tries for logging
            if score <= min_score:
                conc.get_inqueue().put(f'{guess}:{score}')
                min_score = score
                # Exit this process if the load is too high, but make sure to leave at least 1
                # child running. We do the check here so that it doesn't happen too often
                if pid > 0: # Don't stop process 0 until the in-queue is empty
                    if is_cpu_too_busy():
                        break
        except queue.Empty:
            break
        except KeyboardInterrupt:
            return False
    return True

def fill_queue(conc:Concurrent, all_guesses:WordSet) -> None:
    """
    Add all guesses to the input queue for processing.

    Args:
        conc (Concurrent): The concurrent processing object.
        all_guesses (WordSet): The set of guesses to queue.
    """
    for w in all_guesses:
        conc.get_outqueue().put(w)

def launch_child(conc:Concurrent, words:WordSet, pid:int) -> None:
    """
    Start a child process to handle guess scoring.

    Args:
        conc (Concurrent): The concurrent processing object.
        words (WordSet): The set of possible answers.
        pid (int): Process ID.
    """
    p = Process(target = get_guess_score, args = (conc, words, pid))
    p.start()
    conc.add_process(p)

def launch_children(conc:Concurrent, words:WordSet) -> None:
    """
    Start multiple child processes for parallel guess scoring.

    Launches up to the configured number of processes or the number of words, whichever is smaller.

    Args:
        conc (Concurrent): The concurrent processing object.
        words (WordSet): The set of possible answers.
    """
    num_processes = min(config.get_max_child_processes(), len(words))
    logging.info('Starting %d processes', num_processes)
    for proc_num in range(num_processes):
        launch_child(conc, words, proc_num)

def process_accurate_logic_single_threaded(all_guesses:WordSet, words:WordSet) -> dict[str, float]:
    """
    Process all guesses sequentially to find the best one.

    Args:
        all_guesses (WordSet): Guesses to evaluate.
        words (WordSet): Possible answers.

    Returns:
        dict[str, float]: Dictionary of guess to score mappings.
    """
    scores: dict[str, float] = {}
    # Only a few legal answers? Then processes them immediately and return the scores.
    min_score = MAX_WORD_SCORE
    for guess in all_guesses:
        score = accurate(words, guess, min_score)
        # Did we find our new lowest-score guess? Include ties for logging
        if score <= min_score:
            min_score = score
            scores[guess] = score
            logging.debug('guess=%s score=%s', guess, round(score, 3))
    return scores

def collect_results_from_processes(concurrent: Concurrent, scores: dict[str, float], words: WordSet) -> None:
    """
    Collect results from child processes and manage dynamic process scaling.
    """
    last_log = False
    proc_num = num_alive = concurrent.get_num_alive()
    while True:
        try:
            word_and_score = concurrent.get_inqueue().get(block = True, timeout = 0.1)
            # We got a result. Process it.
            last_log = False
            guess, score_str = word_and_score.split(':')
            scores[guess] = float(score_str)
            logging.debug('guess=%s score=%s', guess, round(scores[guess], 3))
        except KeyboardInterrupt:
            logging.debug('KeyboardInterrupt caught processing queue.')
            concurrent.clean_up_dirty(1)
            break
        except queue.Empty:
            try:
                # Nothing in the queue. Check if we are done. Check our system load.
                if not (num_alive := concurrent.get_num_alive()):
                    break
                # Start another child process if the load is too low
                cpu = psutil.cpu_percent(interval = 0.2)
                # Only log a message and launch new children if we've done processing
                # since the last time we checked.
                if not last_log:
                    last_log = True
                    if (num_alive < config.get_max_child_processes() and cpu < MAX_CPU_PERCENT * 0.67):
                        proc_num += 1
                        logging.debug('Launching new child process %s to the existing %d, '
                                      'CPU: %.1f%%', proc_num, num_alive, cpu)
                        launch_child(concurrent, words, proc_num)
                    else:
                        logging.debug('Processes alive: %d, CPU: %.1f%%', num_alive, cpu)
            except KeyboardInterrupt:
                logging.debug('KeyboardInterrupt caught computing load.')
                concurrent.clean_up_dirty(1)
                break

def process_parallel_guesses(all_guesses:WordSet, words:WordSet) -> dict[str, float]:
    """
    Process guesses using parallel child processes.
    """
    scores: dict[str, float] = {}
    concurrent = Concurrent()

    # Queue-up the words to check
    fill_queue(concurrent, all_guesses)

    # Launch the child jobs
    launch_children(concurrent, words)

    # Collect results and manage processes
    collect_results_from_processes(concurrent, scores, words)

    # Clean up the child processes
    if concurrent.is_child_abnormal_exit():
        logging.debug('Child process error.')
        concurrent.clean_up_dirty(2)
    concurrent.join_processes()
    return scores

def process_accurate_logic(all_guesses:WordSet, words:WordSet) -> dict[str, float]:
    """
    Process guesses using parallel processing if beneficial.

    Falls back to single-threaded if not enough words or processes.

    Args:
        all_guesses (WordSet): Guesses to evaluate.
        words (WordSet): Possible answers.

    Returns:
        dict[str, float]: Dictionary of guess to score mappings.
    """
    max_child_processes = config.get_max_child_processes()
    # Only a few legal answers? Then processes them immediately and return the scores.
    if (len(words) < config.get_multi_processes_threshold() or max_child_processes < 2):
        return process_accurate_logic_single_threaded(all_guesses, words)

    return process_parallel_guesses(all_guesses, words)

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
    for i in range(len(results)):
        if scores[results[i]] > lowest_value:
            num_to_log = i
            break

    # Log all entries with the lowest value plus the next entry (if it exists) in reverse order
    for i in range(num_to_log, -1, -1):
        _log_a_score(results, scores, i)

def log_solution_space(words: WordSet) -> None:
    """
    Log information about the current solution space.
    """
    if len(words) < 10:
        logging.info('Solution space is %d word%s=%s',
                     len(words),
                     's' if len(words) > 1 else '',
                     words)
    else:
        logging.info('Solution space is %d words', len(words))
        logging.debug('words=%s', words)

def get_cached_guess(clues: Clues, words: WordSet) -> tuple[str, Logic] | None:
    """
    Attempt to retrieve a cached guess for the second guess optimization.

    Returns the cached guess and logic if available, otherwise None.
    """
    if config.get_use_cache() and clues.get_num_guesses() == 1:
        guess_cache = SecondGuessCache()
        if guess_cache.in_cache(clues):
            (guess, score) = guess_cache.get(clues)
            logic = Logic()
            logic.update('cache lookup', float(score), words)
            return (guess, logic)
    return None

def select_guess_set(dictionary: WordSet, words: WordSet, clues: Clues) -> WordSet:
    """
    Select the set of guesses to evaluate based on remaining possibilities and guesses.
    If there are 3 or less possible answers or if it's our last guess then pick an answer from
    the possible answer set. Otherwise we might want to pick a guess from some known non-answers
    because they might better narrow down the soluiton. But don't use vulgar words.
    """
    return (words
            if len(words) < 3 or clues.get_num_guesses() > config.get_max_guesses() - 2
            else dictionary - vulgar_words())

def find_best_guess(all_guesses: WordSet, words: WordSet) -> tuple[list[str], float]:
    """
    Evaluate all guesses and return all guesses with the minimum score and that score.
    """
    scores = process_accurate_logic(all_guesses, words)
    if not scores:
        return [], MAX_WORD_SCORE
    min_score = min(scores.values())
    best_guesses = [guess for guess, score in scores.items() if score == min_score]
    results = sorted(scores, key=scores.__getitem__)
    _log_a_few_scores(results, scores)
    return best_guesses, min_score

def resolve_guess_ties(best_guesses: list[str], words: WordSet) -> str:
    """
    Resolve ties between equally-scored guesses using meta-scoring with alternate algorithms.
    """
    current_alg = config.get_algorithm()
    other_algs = [alg for alg in [accurate_avg, accurate_median, accurate_max]
                  if alg != current_alg]
    meta_scores = {}
    for guess in best_guesses:
        scores = [alg(words, guess, MAX_WORD_SCORE) for alg in other_algs]
        meta_scores[guess] = sum(scores)
    min_meta = min(meta_scores.values())
    final_candidates = [g for g in best_guesses if meta_scores[g] == min_meta]
    if len(final_candidates) != len(best_guesses):
        logging.info('tie-breaking meta_scores: %s',
                     {k: round(v, 3) for k, v in
                      sorted(meta_scores.items(), key=lambda item: item[1])})
    return random.choice(final_candidates)

def best_guess(dictionary: WordSet, words: WordSet, clues: Clues) -> tuple[str, Logic]:
    """
    Determine the optimal guess from the current word set.

    Uses caching for second guesses if enabled. Selects from all guesses or only answers
    depending on remaining attempts.

    Args:
        dictionary (WordSet): Full set of legal guesses.
        words (WordSet): Current possible answers.
        clues (Clues): Accumulated clues so far.

    Returns:
        tuple[str, Logic]: The best guess and its logic information.
    """
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
        sys.exit(1)

def validate_guess_input(guess: str, dictionary: WordSet, logger, last_guess: str) -> tuple[bool, str]:
    """
    Validate a guess input and return validation result and updated last_guess.
    """
    if len(guess) != config.get_word_length():
        logging.error('%s is does not have %d letters.', guess, config.get_word_length())
        return False, last_guess
    if (guess in dictionary or
         logger.getEffectiveLevel() == logging.DEBUG or
         last_guess == guess):
        return True, last_guess
    else:
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
    logger = logging.getLogger()
    last_guess = ''
    while True:
        print('Guess> ', end = '')
        guess = input_lower()
        valid, last_guess = validate_guess_input(guess, dictionary, logger, last_guess)
        if valid:
            break
    return guess

def is_only_clue_letters(user_clue:str) -> bool:
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
        if len(manual) != config.get_word_length():
            logging.error('Clue must be %d letters long.',config.get_word_length())
        elif not is_only_clue_letters(manual):
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
    word_length = config.get_word_length()
    guess_list = list(guess[:word_length])
    color_list = [''] * word_length
    color_map = {'g':Back.GREEN, 'y':Back.YELLOW, 'b':Back.BLACK}
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

def display_board(clues: Clues, ans: str) -> None:
    """
    Display the full game board with all guesses.

    Args:
        clues (Clues): The clues object.
        ans (str): The answer word.
    """
    for i, guess in enumerate(clues.get_guesses()):
        display_row(i+1, get_clue_list(guess, ans), guess)

def setup_argument_parser(word_list_dictionary: str, max_children: int, logging_levels: dict[str, int]) -> argparse.ArgumentParser:
    """
    Set up and return the argument parser with all command line options.
    """
    parser = argparse.ArgumentParser(prog=sys.argv[0], description='Solve Wordle-like Puzzles')
    parser.add_argument('--answer', '-a', help='the word to solve for when mode=auto')
    parser.add_argument('--mode', '-m', choices=['auto', 'clues', 'advise', 'play'],
                        default='auto',
                        help='auto - will solve for the answer provided (default), '
                        + 'clues - will solve based on the line by line clues that you '
                        + 'provide using letters [gyb], '
                        + 'advise - will suggest guesses and let you provide guesses and '
                        + 'clues, play - will let you play the game')
    parser.add_argument('--start', '-s', default='list', metavar='WORD',
                        help='list - the first guess will be based on a list '
                        + f'{FIRST_GUESS_WORDS} (default), '
                        + 'Otherwise the first guess will be the WORD provided')
    parser.add_argument('--length', '-w', choices=list(range(1,MAX_WORD_LENGTH+1)), default=5,
                        type=int, help='sets the word length (default=5)')
    parser.add_argument('--max', '-x', help='sets the maximum number of guesses (default=6)',
                        default=6, type=int)
    parser.add_argument('--rate-alg', '-r',
                        help='use rating algorithm for scoring guesses. 1=avg, 2=med, 3=max_max',
                        default=1, type=int, choices=[1,2,3])
    parser.add_argument('--processes', '-p',
                        help=f'number of child processes (default={max_children})',
                        default=max_children, type=int)
    parser.add_argument('--no-cache', '-c', dest='cache',
                        help='don\'t use a cache file for second guess performance',
                        default=None, action=argparse.BooleanOptionalAction)
    parser.add_argument('--logging', '-l', choices=logging_levels.keys(), default='error')
    parser.add_argument('--dictionary', '-d', default=word_list_dictionary,
                        help=f'dictionary word list file, default is {word_list_dictionary}')
    return parser

def set_configuration_from_args(args) -> None:
    """
    Set configuration values from parsed command line arguments.
    """
    config.set_max_guesses(args.max)
    config.set_word_length(args.length)
    config.set_mode(args.mode)
    config.set_start(args.start)
    config.set_answer(args.answer)
    config.set_max_child_processes(args.processes)
    config.set_word_list_dictionary(args.dictionary)

    # Convert the user choice into a function pointer
    if args.rate_alg == 1:
        config.set_algorithm(accurate_avg)
    elif args.rate_alg ==2:
        config.set_algorithm(accurate_median)
    else:
        config.set_algorithm(accurate_max)

    # Post-process to set conditional default for cache if not explicitly provided
    if args.cache is None:
        if args.rate_alg == 1:
            config.set_use_cache(True)  # Use cache (equivalent to -c False)
        else:
            config.set_use_cache(False) # Don't use cache (equivalent to -c True)
    else:
        config.set_use_cache(not args.cache)

def setup_logging_from_args(args, logging_levels: dict[str, int]) -> None:
    """
    Configure logging level and output initial configuration info.
    """
    l = logging.getLogger()
    l.setLevel(logging_levels[args.logging])
    logging.info('Options: ans=%s mode=%s start=%s word_len=%d max_guesses=%d use_cache=%s',
                 config.get_answer(), config.get_mode(), config.get_start(),
                 config.get_word_length(), config.get_max_guesses(), config.get_use_cache())
    logging.info('Options: max_child_processes=%d dictionary=%s algorithm=%s',
                 config.get_max_child_processes(), config.get_word_list_dictionary(),
                 config.get_algorithm().__name__)

def parse_command_line() -> None:
    """
    Parse command line arguments and configure the program.

    Sets up logging, word length, modes, etc.
    """
    # Use interval so that it returns a non-zero value
    cpu_percent = psutil.cpu_percent(interval = 0.1) / 100

    cpus = psutil.Process().cpu_affinity() # cpu list
    cpus = [0] if cpus is None else cpus

    # The maximum number of child processes to use is the percent_idle * num_processors
    max_children = max(round((len(cpus) * (1 - cpu_percent) * MAX_CPU_PERCENT) / 100), 0)

    logging_levels = {'critical': logging.CRITICAL,
                      'error': logging.ERROR,
                      'warn': logging.WARNING,
                      'warning': logging.WARNING,
                      'info': logging.INFO,
                      'debug': logging.DEBUG}

    word_list_dictionary = config.get_word_list_dictionary()
    if not pathlib.Path(word_list_dictionary).exists():
        word_list_dictionary = config.get_word_list_dictionary2()
        config.set_word_list_dictionary(word_list_dictionary)

    parser = setup_argument_parser(word_list_dictionary, max_children, logging_levels)
    args = parser.parse_args()

    set_configuration_from_args(args)
    setup_logging_from_args(args, logging_levels)

class Mode():
    """
    Base class for different game modes.

    Subclasses implement mode-specific behavior for guess display and input.
    """

    @staticmethod
    def print_raw_guess(guess:str, row: int, logic: Logic) -> Logic:
        """no-op"""
        # pylint: disable=unused-argument
        return logic

    @staticmethod
    def get_user_guess(dictionary: WordSet, guess: str, words: WordSet,
                       clues: Clues, logic: Logic) -> str:
        """no-op"""
        # pylint: disable=unused-argument
        return guess

    @staticmethod
    def get_clue(guess: str, ans: str) -> LetterList:
        """Get the clue from the user if we don't already know it."""
        return  get_clue_list(guess, ans) if ans else get_user_clue()


class ModeAdvise(Mode):
    """
    Mode for advising the user on guesses while allowing custom input.
    """

    @staticmethod
    def print_raw_guess(guess: str, row: int, logic: Logic) -> Logic:
        print(f'{str(row)} Recommendation: {guess.upper()} [{str(logic)}]')
        return logic

    @staticmethod
    def get_user_guess(dictionary: WordSet, guess: str, words: WordSet,
                       clues: Clues, logic: Logic) -> str:
        start = config.get_start()
        user_guess = (start
                      if len(start) == config.get_word_length() and clues.get_num_guesses() == 0
                      else input_guess(dictionary))
        score = accurate(words, user_guess, MAX_WORD_SCORE)
        logic.update('user input', score, words)
        logging.info('guess=%s score=%s', user_guess, round(score, 3))
        return user_guess


class ModeClues(Mode):
    """
    Mode for solving based on user-provided clues.
    """

    @staticmethod
    def print_raw_guess(guess: str, row: int, logic: Logic) -> Logic:
        print(f'{str(row)} {guess.upper()} [{str(logic)}]')
        return logic


class ModePlay(Mode):
    """
    Mode for interactive play where the program selects the answer.
    """

    @staticmethod
    def get_user_guess(dictionary: WordSet, guess: str, words: WordSet,
                       clues: Clues, logic: Logic) -> str:
        return ModeAdvise.get_user_guess(dictionary, guess,words, clues, logic)


def obtain_answer(legal_answers: WordSet) -> str:
    """
    Select or validate the answer word based on mode.

    Args:
        legal_answers (WordSet): Valid answer words.

    Returns:
        str: The chosen answer.
    """
    mode = config.get_mode()
    answer = config.get_answer()
    word_length = config.get_word_length()
    if mode in {'auto', 'play'}:
        if not answer:
            answer = random_word(legal_answers)
            config.set_answer(answer)
            if mode == 'auto':
                logging.info('Chose %s as the answer.', answer.upper())
        elif answer not in legal_answers:
            logging.error('%s is not a recognized word', answer)
            if len(answer) != word_length:
                logging.error('%s does not have %d letters', answer, word_length)
                sys.exit(0)
    return answer

def initialize_game() -> tuple[WordSet, WordSet, Clues, str, str, Logic, type]:
    """
    Initialize the game state and setup initial parameters.
    """
    start = config.get_start()
    word_length = config.get_word_length()
    logger = logging.getLogger()

    (legal_guesses, legal_answers) = build_dictionaries()
    legal_answers = legal_answers.copy()

    clues = Clues()

    # Pick a random answer if none given. Make sure the answer
    # given by the user is legit.
    answer = obtain_answer(legal_answers)

    # We only have a starting word list for words of length=5
    if start == 'list' and word_length != 5:
        logging.warning('Starting word "list" option only available for word length 5')

    # Figure-out the first guess
    guess = ''
    logic = Logic()
    if start == 'list':
        start_word_list = FIRST_GUESS_WORDS if word_length == 5 else legal_answers
        guess = random_word(start_word_list)
        logic.update('predefined list', 0, start_word_list)
    else:
        guess = start
        logic.update('starting word provided', 0, {start})

    # Make sure the starting guess is legit, unless we are in debug mode
    if (guess not in legal_guesses and logger.getEffectiveLevel() != logging.DEBUG):
        logging.error('%s is not a recognized word\n', guess)

    # We use the mode_class to handle the logic that is different for different modes
    mode_class = {
        'advise': ModeAdvise,
        'clues': ModeClues,
        'auto': Mode,
        'play': ModePlay}[config.get_mode()]

    return legal_guesses, legal_answers, clues, answer, guess, logic, mode_class

def execute_game_rounds(legal_guesses: WordSet, legal_answers: WordSet, clues: Clues, answer: str, guess: str, logic: Logic, mode_class: type) -> str:
    """
    Execute the main game rounds loop until completion.
    """
    word_length = config.get_word_length()
    for row_num in range(1, config.get_max_guesses() + 1):
        logic = mode_class.print_raw_guess(guess, row_num, logic)
        try:
            guess = mode_class.get_user_guess(legal_guesses, guess, legal_answers, clues, logic)
        except KeyboardInterrupt:
            logging.debug('KeyboardInterrupt while getting user guess.')
            sys.exit(1)
        else:
            clue_list = mode_class.get_clue(guess, answer)
            clues.add_clue(guess, clue_list)
            logging.debug('%d guess=%s %s', row_num, guess, clues)
            display_row(row_num,clue_list,guess, str(logic) if config.get_mode() != 'play' else '')
            if clue_list == ['g']*word_length:
                print(f'Solved for {guess.upper()} in {row_num} guesses')
                return guess
            if row_num == config.get_max_guesses():
                print('Better luck next time!')
                if answer:
                    print(f'The answer is: {answer.upper()}')
                return guess
            legal_answers = clues.filter_words(legal_answers)
            guess, logic = best_guess(legal_guesses, legal_answers, clues)
    return guess

def game_loop() -> None:
    """
    Run the main game loop, processing guesses and clues.
    """

    legal_guesses, legal_answers, clues, answer, guess, logic, mode_class = initialize_game()

    final_guess = execute_game_rounds(legal_guesses, legal_answers, clues, answer, guess, logic, mode_class)

    # Show the final board
    display_board(clues, answer if answer else final_guess)

def main() -> None:
    """
    Main entry point: set up logging, parse args, and start the game.
    """ 

    logging.basicConfig(level = logging.ERROR, format = '[%(levelname)s] %(asctime)s - %(message)s')

    parse_command_line()

    # Play the game!
    game_loop()

if __name__ == '__main__':
    main()
