# SPDX-FileCopyrightText: 2026 Steven M. Gale
# SPDX-License-Identifier: GPL-3.0-or-later

"""Regression tests for atomic cache publication and retryable reads."""

import json
from pathlib import Path

import pytest

from config import Config
from second_guess import SecondGuessCache


def make_cache(tmp_path):
    Config().set_cache_dir(str(tmp_path))
    cache = SecondGuessCache()
    cache.add2('crane;bbbbb', 'sissy', 1.0)
    cache.serialize()
    cache.add2('crane;bbgbg', 'slate', 1.0)
    return cache, tmp_path / 'wordle_cache.json'


def test_readers_see_complete_old_file_until_replacement(tmp_path, monkeypatch):
    cache, path = make_cache(tmp_path)
    old_contents = path.read_text(encoding='utf-8')
    replace = Path.replace
    publications = []

    def inspect_replacement(temporary, destination):
        assert temporary.parent == path.parent
        assert destination == path
        assert path.read_text(encoding='utf-8') == old_contents
        payload = json.loads(temporary.read_text(encoding='utf-8'))
        assert 'crane;bbgbg' in payload['entries']
        publications.append(temporary)
        return replace(temporary, destination)

    monkeypatch.setattr(Path, 'replace', inspect_replacement)
    cache.serialize()
    assert len(publications) == 1
    assert 'crane;bbgbg' in json.loads(path.read_text(encoding='utf-8'))['entries']
    assert list(tmp_path.iterdir()) == [path]


def test_failed_replacement_preserves_file_and_can_retry(tmp_path, monkeypatch):
    cache, path = make_cache(tmp_path)
    old_contents = path.read_text(encoding='utf-8')

    def fail_replacement(*args):
        raise OSError('simulated replacement failure')

    with monkeypatch.context() as patch:
        patch.setattr(Path, 'replace', fail_replacement)
        with pytest.raises(OSError, match='simulated replacement failure'):
            cache.serialize()

    assert path.read_text(encoding='utf-8') == old_contents
    assert list(tmp_path.iterdir()) == [path]
    cache.serialize()
    assert 'crane;bbgbg' in json.loads(path.read_text(encoding='utf-8'))['entries']


def test_failed_read_does_not_consume_file_timestamp(tmp_path, monkeypatch):
    cache, path = make_cache(tmp_path)
    # No compatibility check is needed for publication tests; use a valid
    # metadata header here to exercise the complete loading path.
    payload = json.loads(path.read_text(encoding='utf-8'))
    payload['metadata'] = {'version': 3}
    path.write_text(json.dumps(payload), encoding='utf-8')
    cache._cache_stamp = 0.0
    original_load = json.load
    reads = []

    def interrupted_read(stream):
        reads.append(True)
        if len(reads) == 1:
            raise json.JSONDecodeError('incomplete write', '', 0)
        return original_load(stream)

    monkeypatch.setattr(json, 'load', interrupted_read)
    cache.load()
    assert cache.in_cache2('crane;bbbbb')
    cache.load()
    assert len(reads) == 2
