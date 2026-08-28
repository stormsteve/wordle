# SPDX-FileCopyrightText: 2026 Steven M. Gale
# SPDX-License-Identifier: GPL-3.0-or-later

"""
Command line argument parsing for Wordle game.
"""

# Local imports keep optional dependencies and GUI startup lazy.
# pylint: disable=import-outside-toplevel

import argparse
import pathlib
from config import Config


def _positive_int(value: str) -> int:
    """Parse an integer that must be at least one."""
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError('must be at least 1')
    return parsed


def _non_negative_int(value: str) -> int:
    """Parse an integer that may be zero but not negative."""
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError('must be zero or greater')
    return parsed


def setup_argument_parser(
        word_list_dictionary: str,
        max_children: int,
        logging_levels: dict[str, int]) -> argparse.ArgumentParser:
    """
    Set up and return the argument parser with all command line options.
    """
    parser = argparse.ArgumentParser(prog='wordle.py', description='Solve Wordle-like Puzzles')
    parser.add_argument('--gui', action='store_true',
                        help='launch the desktop GUI front end')
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
                        + '(default), '
                        + 'Otherwise the first guess will be the WORD provided')
    parser.add_argument('--length', '-w', choices=list(range(1, 20)), default=5,  # Assuming max 19
                        type=int, help='sets the word length (default=5)')
    parser.add_argument('--max', '-x', help='sets the maximum number of guesses (default=6)',
                        default=6, type=_positive_int)
    parser.add_argument('--rate-alg', '-r',
                        help='use rating algorithm for scoring guesses. 1=avg, 2=med, 3=max_max',
                        default=1, type=int, choices=[1,2,3])
    parser.add_argument('--processes', '-p',
                        help=f'number of child processes (default={max_children})',
                        default=max_children, type=_non_negative_int)
    parser.add_argument('--no-cache', '-c', dest='cache',
                        help='don\'t use a cache file for second guess performance',
                        default=None, action='store_true')
    parser.add_argument('--cache-dir', default='.', metavar='DIR',
                        help='directory for the cache file (default: current directory)')
    parser.add_argument('--logging', '-l', choices=logging_levels.keys(), default='error')
    parser.add_argument('--dictionary', '-d', default=word_list_dictionary,
                        help=f'dictionary word list file, default is {word_list_dictionary}')
    return parser


def set_configuration_from_args(args) -> None:
    """
    Set configuration values from parsed command line arguments.
    """
    config = Config()
    config.set_max_guesses(args.max)
    config.set_word_length(args.length)
    config.set_mode(args.mode)
    config.set_start(args.start.strip().lower())
    config.set_answer(args.answer.strip().lower() if args.answer else None)
    config.set_max_child_processes(args.processes)
    config.set_word_list_dictionary(args.dictionary)
    config.set_cache_dir(getattr(args, 'cache_dir', '.'))

    # Convert the user choice into a function pointer
    from algorithm import accurate_avg, accurate_median, accurate_max
    if args.rate_alg == 1:
        config.set_algorithm(accurate_avg)
    elif args.rate_alg == 2:
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
    import logging
    l = logging.getLogger()
    l.setLevel(logging_levels[args.logging])
    config = Config()
    logging.info('Options: ans=%s mode=%s start=%s word_len=%d max_guesses=%d use_cache=%s',
                 config.get_answer(), config.get_mode(), config.get_start(),
                 config.get_word_length(), config.get_max_guesses(), config.get_use_cache())
    logging.info(
        'Options: max_child_processes=%d dictionary=%s algorithm=%s',
        config.get_max_child_processes(), config.get_word_list_dictionary(),
        config.get_algorithm().__name__)


def parse_command_line() -> argparse.Namespace:
    """
    Parse command line arguments and configure the program.

    Sets up logging, word length, modes, etc.
    """
    import psutil
    # Use interval so that it returns a non-zero value
    cpu_percent = psutil.cpu_percent(interval = 0.1) / 100

    try:
        cpus = psutil.Process().cpu_affinity()  # cpu list
    except (AttributeError, NotImplementedError, psutil.AccessDenied):
        cpu_count = psutil.cpu_count(logical = True) or 1
        cpus = list(range(cpu_count))
    cpus = [0] if cpus is None else cpus

    config = Config()
    # The maximum number of child processes to use is the percent_idle * num_processors
    max_children = max(
        round((len(cpus) * (1 - cpu_percent) * config.get_max_cpu_percent()) / 100), 0)

    logging_levels = {'critical': 50,  # logging.CRITICAL
                      'error': 40,     # logging.ERROR
                      'warn': 30,      # logging.WARNING
                      'warning': 30,   # logging.WARNING
                      'info': 20,      # logging.INFO
                      'debug': 10}     # logging.DEBUG

    word_list_dictionary = config.get_word_list_dictionary()
    if not pathlib.Path(word_list_dictionary).exists():
        bundled_dictionary = pathlib.Path(__file__).resolve().parent / word_list_dictionary
        word_list_dictionary = (
            str(bundled_dictionary) if bundled_dictionary.exists()
            else config.get_word_list_dictionary2())
        config.set_word_list_dictionary(word_list_dictionary)

    parser = setup_argument_parser(word_list_dictionary, max_children, logging_levels)
    args = parser.parse_args()

    set_configuration_from_args(args)
    setup_logging_from_args(args, logging_levels)
    return args
