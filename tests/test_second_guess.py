# SPDX-FileCopyrightText: 2026 Steven M. Gale
# SPDX-License-Identifier: GPL-3.0-or-later

"""Regression coverage for cache compatibility and guess restrictions."""

import pytest
import json

from algorithm import accurate_avg, accurate_max
from best_guess import get_cached_guess
from clues import Clues
from config import Config
from second_guess import SecondGuessCache


def test_cache_context_survives_reload_across_word_lists(tmp_path):
    config = Config()
    config.set_cache_dir(str(tmp_path))
    config.set_algorithm(accurate_avg)
    dictionary = {'sissy', 'bully', 'hussy', 'adieu'}
    words = dictionary - {'adieu'}
    clues = Clues()
    clues.add_clue('crane', list('bbbbb'))
    cache = SecondGuessCache()
    cache.set_context(dictionary, words)
    cache.add(clues, 'adieu', 1.5)
    cache.serialize()
    loaded = SecondGuessCache()
    loaded.set_context(set(reversed(sorted(dictionary))), words)
    assert loaded.get(clues) == ('adieu', 1.5)
    loaded.set_context(dictionary | {'extra'}, words)
    assert loaded.get(clues) == ('adieu', 1.5)
    loaded.set_context(dictionary, {'sissy'})
    assert loaded.get(clues) == ('adieu', 1.5)
    config.set_algorithm(accurate_max)
    loaded.set_context(dictionary, words)
    assert not loaded.in_cache(clues)
    config.set_algorithm(accurate_avg)
    config.set_word_length(6)
    loaded.set_context(dictionary, words)
    assert not loaded.in_cache(clues)


def test_legacy_cache_is_not_used_for_contextual_lookup(tmp_path):
    config = Config()
    config.set_cache_dir(str(tmp_path))
    config.set_use_cache(True)
    clues = Clues()
    clues.add_clue('crane', list('bbbbb'))
    cache = SecondGuessCache()
    cache.add(clues, 'slate', 1.0)
    cache.serialize()
    assert get_cached_guess(clues, {'sissy'}, {'sissy', 'slate'}, {'sissy'}) is None


@pytest.mark.parametrize('max_guesses,legal,expected', [
    (6, True, 'adieu'),
    (2, True, None),
    (6, False, None),
])
def test_cache_hit_respects_dictionary_and_final_attempt(
        monkeypatch, tmp_path, max_guesses, legal, expected):
    import best_guess
    config = Config()
    config.set_cache_dir(str(tmp_path))
    config.set_max_guesses(max_guesses)
    config.set_use_cache(True)
    words = {'sissy', 'bully', 'hussy'}
    dictionary = words | ({'adieu'} if legal else set())
    clues = Clues()
    clues.add_clue('crane', list('bbbbb'))
    cache = SecondGuessCache()
    cache.set_context(dictionary, words)
    cache.add(clues, 'adieu', 1.0)
    monkeypatch.setattr(best_guess, 'SecondGuessCache', lambda: cache)
    result = get_cached_guess(clues, words, dictionary, words)
    assert (result[0] if result else None) == expected


def test_metadata_is_word_list_independent_and_row_keys_stay_short(tmp_path):
    Config().set_cache_dir(str(tmp_path))
    cache = SecondGuessCache()
    cache.set_context({'crane', 'slate'}, {'slate'})
    for word in ('crane', 'slate'):
        clues = Clues()
        clues.add_clue(word, list('bbbbb'))
        cache.add(clues, 'slate', 1.5)
        assert cache.in_cache(clues)
    cache.serialize()
    payload = json.loads((tmp_path / 'wordle_cache.json').read_text(encoding='utf-8'))
    assert set(payload) == {'metadata', 'entries'}
    assert payload['metadata']['version'] == 3
    assert payload['metadata']['algorithm'] == 'algorithm.accurate_avg'
    assert set(payload['metadata']) == {'version', 'word_length', 'algorithm'}
    assert set(payload['entries']) == {'crane;bbbbb', 'slate;bbbbb'}
    loaded = SecondGuessCache({'crane'})
    assert not loaded.in_cache2('crane;bbbbb')
    assert loaded.in_cache2('slate;bbbbb')


def test_different_second_guess_patterns_share_file_metadata(tmp_path):
    config = Config()
    config.set_cache_dir(str(tmp_path))
    config.set_use_cache(True)
    dictionary = {'crane', 'slate', 'sissy'}
    answers = {'slate', 'sissy'}
    cache = SecondGuessCache()
    cache.set_context(dictionary, answers)
    for answer in answers:
        from clue_list import get_clue_list
        clues = Clues()
        clues.add_clue('crane', get_clue_list('crane', answer))
        cache.add(clues, answer, 0.0)
    cache.serialize()
    for answer in answers:
        clues = Clues()
        clues.add_clue('crane', get_clue_list('crane', answer))
        result = get_cached_guess(clues, {answer}, dictionary, answers)
        assert result[0] == answer
