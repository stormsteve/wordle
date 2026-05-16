# SPDX-FileCopyrightText: 2026 Steve Gale <galesteven@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Tests for command-line parsing helpers."""

from argparse import Namespace

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
