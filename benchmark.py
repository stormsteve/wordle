#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Steven M. Gale
# SPDX-License-Identifier: GPL-3.0-or-later

"""Benchmark deterministic samples of Wordle guess scoring."""

import argparse
import hashlib
import json
import logging
import platform
import statistics
import time

import psutil

from algorithm import accurate_avg, accurate_max, accurate_median
from argument_parser import _non_negative_int, _positive_int
from config import Config
from dictionary import build_dictionaries, get_dictionary_source
from myconcurrent import process_accurate_logic
from mytypes import WordCollection


ALGORITHMS = {
    'average': accurate_avg,
    'median': accurate_median,
    'maximum': accurate_max,
}


def select_evenly_spaced(words: set[str], count: int) -> list[str]:
    """Return a deterministic, evenly spaced sample from sorted words."""
    ordered_words = sorted(words)
    if count > len(ordered_words):
        raise ValueError(f'requested {count} words, but only {len(ordered_words)} are available')
    if count == len(ordered_words):
        return ordered_words
    return [ordered_words[index * len(ordered_words) // count] for index in range(count)]


def build_parser() -> argparse.ArgumentParser:
    """Create the benchmark command-line parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--length', type=int, choices=range(1, 20), default=5,
                        help='word length (default: 5)')
    parser.add_argument('--dictionary', help='source word-list path (default: project setting)')
    parser.add_argument('--guess-count', type=_positive_int, default=200,
                        help='number of guesses to score (default: 200)')
    parser.add_argument('--answer-count', type=_positive_int, default=200,
                        help='number of possible answers (default: 200)')
    parser.add_argument('--repeats', type=_positive_int, default=5,
                        help='timed repetitions (default: 5)')
    parser.add_argument('--warmups', type=_non_negative_int, default=1,
                        help='untimed warm-up repetitions (default: 1)')
    parser.add_argument('--processes', type=_non_negative_int, default=0,
                        help='worker processes; 0 forces single-process mode (default: 0)')
    parser.add_argument('--algorithm', choices=ALGORITHMS, default='average',
                        help='scoring algorithm (default: average)')
    return parser


def _load_samples(
        args: argparse.Namespace, config: Config
        ) -> tuple[set[str], set[str], list[str], list[str], float, str]:
    """Load dictionaries and select deterministic guess and answer samples."""
    started = time.perf_counter()
    legal_guesses, legal_answers = build_dictionaries()
    dictionary_seconds = time.perf_counter() - started
    try:
        guess_sample = select_evenly_spaced(legal_guesses, args.guess_count)
        answer_sample = select_evenly_spaced(legal_answers, args.answer_count)
    except ValueError as error:
        raise ValueError(f'{error}; reduce the requested sample size') from error
    return (legal_guesses, legal_answers, guess_sample, answer_sample,
            dictionary_seconds,
            get_dictionary_source(config.get_word_list_dictionary(), args.length, config))


def _measure_samples(args: argparse.Namespace, guesses: list[str],
                     answers: WordCollection) -> tuple[list[float], list[int]]:
    """Run untimed warm-ups and collect scoring durations."""
    for _ in range(args.warmups):
        process_accurate_logic(guesses, answers)
    durations = []
    returned_score_counts = []
    for _ in range(args.repeats):
        started = time.perf_counter()
        scores = process_accurate_logic(guesses, answers)
        durations.append(time.perf_counter() - started)
        returned_score_counts.append(len(scores))
    return durations, returned_score_counts


def execution_details(processes: int, answer_count: int,
                      multiprocessing_threshold: int) -> tuple[str, int]:
    """Return the selected scoring mode and its initial worker count."""
    if processes < 2 or answer_count < multiprocessing_threshold:
        return 'single-process', 0
    return 'multiprocessing', min(processes, answer_count)


def run_benchmark(args: argparse.Namespace) -> dict:
    """Load the selected dictionary, run scoring, and return a result record."""
    config = Config()
    config.set_word_length(args.length)
    config.set_max_child_processes(args.processes)
    config.set_algorithm(ALGORITHMS[args.algorithm])
    config.set_use_cache(False)
    if args.dictionary:
        config.set_word_list_dictionary(args.dictionary)

    (legal_guesses, legal_answers, guess_sample, answer_sample,
     dictionary_seconds, dictionary_source) = _load_samples(args, config)
    # A dict preserves answer iteration order across processes and hash seeds
    # while keeping the scorer's membership tests constant-time.
    answers = dict.fromkeys(answer_sample)
    durations, returned_score_counts = _measure_samples(args, guess_sample, answers)
    scoring_mode, initial_workers = execution_details(
        args.processes, len(answers), config.get_multi_processes_threshold())

    sample_digest = hashlib.sha256(
        ('\n'.join(guess_sample) + '\0' + '\n'.join(answer_sample)).encode('utf-8')
    ).hexdigest()
    return {
        'python': platform.python_version(),
        'platform': platform.platform(),
        'logical_cpus': psutil.cpu_count(logical=True),
        'word_length': args.length,
        'dictionary_source': dictionary_source,
        'legal_guess_count': len(legal_guesses),
        'legal_answer_count': len(legal_answers),
        'guess_sample_count': len(guess_sample),
        'answer_sample_count': len(answer_sample),
        'workload_sha256': sample_digest,
        'algorithm': args.algorithm,
        'requested_processes': args.processes,
        'scoring_mode': scoring_mode,
        'initial_worker_processes': initial_workers,
        'cache_used': False,
        'dictionary_load_seconds': round(dictionary_seconds, 6),
        'warmups': args.warmups,
        'repeats': args.repeats,
        'returned_score_counts': returned_score_counts,
        'scoring_seconds': [round(duration, 6) for duration in durations],
        'median_scoring_seconds': round(statistics.median(durations), 6),
    }


def main() -> None:
    """Run the benchmark and print a JSON result record."""
    logging.basicConfig(level=logging.WARNING)
    parser = build_parser()
    args = parser.parse_args()
    try:
        result = run_benchmark(args)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
