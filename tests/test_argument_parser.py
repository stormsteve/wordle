# SPDX-FileCopyrightText: 2026 Steven M. Gale
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for command-line parsing helpers."""

from argparse import Namespace

import pytest

from algorithm import accurate_avg, accurate_max, accurate_median
from argument_parser import set_configuration_from_args, setup_argument_parser
from config import Config


def test_setup_argument_parser_uses_expected_defaults():
    parser = setup_argument_parser("words.txt", 3, {"error": 40, "debug": 10})

    args = parser.parse_args([])

    assert args.mode == "auto"
    assert args.start == "list"
    assert args.length == 5
    assert args.max == 6
    assert args.processes == 3
    assert args.dictionary == "words.txt"
    assert args.logging == "error"
    assert args.cache is None


def test_set_configuration_from_args_selects_average_algorithm_and_enables_cache():
    config = Config()

    set_configuration_from_args(
        Namespace(
            max=8,
            length=6,
            mode="advise",
            start="crane",
            answer="planet",
            processes=2,
            dictionary="custom.txt",
            rate_alg=1,
            cache=None,
        )
    )

    assert config.get_max_guesses() == 8
    assert config.get_word_length() == 6
    assert config.get_mode() == "advise"
    assert config.get_start() == "crane"
    assert config.get_answer() == "planet"
    assert config.get_max_child_processes() == 2
    assert config.get_word_list_dictionary() == "custom.txt"
    assert config.get_algorithm() is accurate_avg
    assert config.get_use_cache() is True


def test_set_configuration_from_args_normalizes_word_arguments():
    config = Config()

    set_configuration_from_args(
        Namespace(
            max=6,
            length=5,
            mode="auto",
            start="  CrAnE ",
            answer=" PlAnEt ",
            processes=0,
            dictionary="words.txt",
            rate_alg=1,
            cache=None,
        )
    )

    assert config.get_start() == "crane"
    assert config.get_answer() == "planet"


@pytest.mark.parametrize("option", ["--max", "--processes"])
def test_parser_rejects_negative_limits(option):
    parser = setup_argument_parser("words.txt", 3, {"error": 40, "debug": 10})

    with pytest.raises(SystemExit):
        parser.parse_args([option, "-1"])


def test_parser_allows_zero_processes_but_not_zero_guesses():
    parser = setup_argument_parser("words.txt", 3, {"error": 40, "debug": 10})

    assert parser.parse_args(["--processes", "0"]).processes == 0
    with pytest.raises(SystemExit):
        parser.parse_args(["--max", "0"])


def test_set_configuration_from_args_selects_median_algorithm_and_disables_cache_by_default():
    config = Config()

    set_configuration_from_args(
        Namespace(
            max=6,
            length=5,
            mode="auto",
            start="list",
            answer=None,
            processes=0,
            dictionary="words.txt",
            rate_alg=2,
            cache=None,
        )
    )

    assert config.get_algorithm() is accurate_median
    assert config.get_use_cache() is False


def test_set_configuration_from_args_selects_max_algorithm_and_honors_no_cache_flag():
    config = Config()

    set_configuration_from_args(
        Namespace(
            max=6,
            length=5,
            mode="auto",
            start="list",
            answer=None,
            processes=0,
            dictionary="words.txt",
            rate_alg=3,
            cache=True,
        )
    )

    assert config.get_algorithm() is accurate_max
    assert config.get_use_cache() is False
