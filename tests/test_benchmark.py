# SPDX-FileCopyrightText: 2026 Steven M. Gale
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for the benchmark workload selection and CLI defaults."""

import pytest
import json
import os
from pathlib import Path
import subprocess
import sys

import benchmark
from benchmark import build_parser, execution_details, select_evenly_spaced


def test_evenly_spaced_sample_is_deterministic():
    assert select_evenly_spaced({'delta', 'alpha', 'charlie', 'bravo'}, 2) == [
        'alpha', 'charlie']


def test_evenly_spaced_sample_returns_all_words_when_requested():
    assert select_evenly_spaced({'bravo', 'alpha'}, 2) == ['alpha', 'bravo']


def test_evenly_spaced_sample_rejects_oversized_request():
    with pytest.raises(ValueError, match='only 1 are available'):
        select_evenly_spaced({'alpha'}, 2)


def test_benchmark_cli_defaults_to_small_single_process_run():
    args = build_parser().parse_args([])

    assert args.guess_count == 200
    assert args.answer_count == 200
    assert args.repeats == 5
    assert args.warmups == 1
    assert args.processes == 0


@pytest.mark.parametrize(('processes', 'answers', 'expected'), [
    (0, 200, ('single-process', 0)),
    (1, 200, ('single-process', 0)),
    (4, 5, ('single-process', 0)),
    (4, 20, ('multiprocessing', 4)),
    (8, 3, ('single-process', 0)),
])
def test_execution_details_report_actual_scoring_mode(processes, answers, expected):
    assert execution_details(processes, answers, 10) == expected


def test_benchmark_passes_ordered_guess_sample_to_scorer(monkeypatch):
    args = build_parser().parse_args([
        '--guess-count', '2', '--answer-count', '2', '--repeats', '2', '--warmups', '1'])
    seen_guesses = []

    def fake_scorer(guesses, _answers):
        seen_guesses.append(guesses)
        return {}

    monkeypatch.setattr(benchmark, 'process_accurate_logic', fake_scorer)

    benchmark._measure_samples(args, ['alpha', 'bravo'], {'answer', 'other'})

    assert seen_guesses == [['alpha', 'bravo']] * 3


def test_benchmark_preserves_answer_order_and_labels_returned_scores(monkeypatch):
    args = build_parser().parse_args([
        '--guess-count', '2', '--answer-count', '2', '--repeats', '1', '--warmups', '0'])
    seen_answers = []

    def fake_scorer(_guesses, answers):
        seen_answers.extend(answers)
        return {'alpha': 1.0}

    monkeypatch.setattr(benchmark, 'build_dictionaries',
                        lambda: ({'bravo', 'alpha'}, {'bravo', 'alpha'}))
    monkeypatch.setattr(benchmark, 'process_accurate_logic', fake_scorer)
    result = benchmark.run_benchmark(args)

    assert seen_answers == ['alpha', 'bravo']
    assert result['returned_score_counts'] == [1]
    assert 'scored_guess_counts' not in result


def test_scoring_work_is_identical_across_hash_seeds():
    script = '''
import json
from benchmark import build_parser, run_benchmark
from clues import Clues
calls = 0
original = Clues.filter_words_len
def counted(self, words, limit=None):
    global calls
    calls += 1
    return original(self, words, limit)
Clues.filter_words_len = counted
args = build_parser().parse_args([
    '--guess-count', '80', '--answer-count', '80', '--repeats', '1', '--warmups', '0'])
result = run_benchmark(args)
print(json.dumps([result['workload_sha256'], calls, result['returned_score_counts']]))
'''
    results = []
    for seed in ('1', '2'):
        completed = subprocess.run(
            [sys.executable, '-c', script],
            cwd=Path(benchmark.__file__).resolve().parent,
            env={**os.environ, 'PYTHONHASHSEED': seed},
            capture_output=True, text=True, check=True, timeout=20)
        results.append(json.loads(completed.stdout))

    assert results[0] == results[1]
