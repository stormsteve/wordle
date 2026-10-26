# Wordle

Everything Wordle -- Play, Solve, Assist

`wordle` is a Python toolkit for Wordle: solve known answers, narrow candidates from clue patterns, get interactive guess advice, or play locally through either the CLI or the Tkinter GUI.

## Features

- CLI solver with `auto`, `clues`, `advise`, and `play` modes
- Desktop GUI launched with `--gui`
- Search and scoring helpers for choosing strong guesses
- Adjustable word length for Wordle-like variants
- Parallel processing support for heavier guess evaluation
- Selectable optimization algorithms for guess scoring
- Configurable dictionary input files
- Optional cache builder for second-guess performance
- Test suite covering the main solver and interface modules

## Requirements

- Python 3.12 or newer recommended
- `psutil`
- `colorama`
- `tkinter` for the GUI (optional)

For a clean Ubuntu setup, install Python, create an isolated environment, and
install the development requirements (which include runtime requirements):

```bash
sudo apt-get update
sudo apt-get install python3 python3-venv
git clone https://github.com/stormsteve/wordle.git
cd wordle
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
```

Optional Ubuntu packages:

```bash
sudo apt-get install python3-tk  # GUI support
sudo apt-get install wamerican  # system dictionary for non-five-letter games
```

For a runtime-only environment, install `requirements.txt` instead of
`requirements-dev.txt`.


## Quick Start

The default five-letter game uses the tracked `legal_guesses.txt` and
`legal_answers.txt` files, so it does not depend on a host-provided dictionary.
Run the CLI:

```bash
python3 wordle.py
```

Launch the GUI:

```bash
python3 wordle.py --gui
```

Solve for a known answer:

```bash
python3 wordle.py --mode auto --answer crane
```

Get interactive solving help:

```bash
python3 wordle.py --mode advise
```

Use a custom word length:

```bash
python3 wordle.py --length 6
```

Choose a different scoring algorithm:

```bash
python3 wordle.py --rate-alg 2
```

Increase worker processes for heavier searches:

```bash
python3 wordle.py --processes 8
```

Run tests:

```bash
pytest
```

## Command-line options

Use `python3 wordle.py --help` for the complete generated help. The main
options are:

| Option | Purpose |
| --- | --- |
| `--mode {auto,clues,advise,play}` | Solve a known answer, enter clues, get advice, or play. |
| `--answer WORD` | Answer to solve in `auto` mode. |
| `--start WORD` | Opening guess; defaults to the configured list. |
| `--length N` | Word length, from 1 to 19 (default: 5). |
| `--max N` | Maximum guesses (default: 6). |
| `--rate-alg {1,2,3}` | Choose average, median, or maximum scoring. |
| `--processes N` | Maximum child workers; `0` uses single-process scoring. |
| `--dictionary PATH` | Source word list; non-five-letter games need a source list. |
| `--no-cache` | Disable cached second-guess recommendations. |
| `--cache-dir DIR` | Cache location (default: current directory). |
| `--gui` | Launch the Tkinter interface. |
| `--logging LEVEL` | Set output detail (`error`, `info`, `debug`, etc.). |

## Benchmarking

Run a repeatable sample of the solver's guess-scoring workload:

```bash
python3 benchmark.py
```

The script uses evenly spaced words from the sorted legal-guess and answer
sets, performs one warm-up, then reports each timed run and the median as JSON.
It bypasses the cache. To compare single-process and parallel scoring, use the
same workload settings and change only `--processes`:

```bash
python3 benchmark.py --guess-count 200 --answer-count 200 --processes 0
python3 benchmark.py --guess-count 200 --answer-count 200 --processes 4
```

The output includes the workload hash, effective dictionary source, and
selected scoring mode; compare runs only when their workload hashes,
algorithm, and dictionary settings match. Use
`--dictionary PATH` for a custom word list and `--length` for other word sizes.
Guess and answer iteration order is fixed. Parallel worker scheduling and
load-based scaling can still affect pruning and timings. The
`returned_score_counts` field counts retained score results, not scoring calls;
every sampled guess is attempted in each completed repetition.

### Example results

On a Windows 11 Home 26H2 host running WSL2 (Linux kernel
`6.18.54.1-microsoft-standard-WSL2`), with an Intel Core Ultra 9 185H,
32 GB host RAM, Ubuntu 26.04.1 LTS, Python 3.14.4, and 16 CPUs available to
the WSL process (CPU IDs 0–15), scoring 200 guesses against 200 answers with
the average algorithm produced these medians. WSL reported 15 GiB total
memory and 4 GiB swap; at measurement time, 14 GiB memory and all swap were
available.

| Processes | Median | Range across 5 runs | Speedup vs. 1 process |
| ---: | ---: | ---: | ---: |
| 0 (single-process) | 1.476 s | 1.462–1.501 s | 1.00× |
| 4 | 0.929 s | 0.880–1.110 s | 1.59× |
| 8 | 0.743 s | 0.728–0.759 s | 1.99× |
| 12 | 0.736 s | 0.711–0.800 s | 2.01× |
| 16 | 1.048 s | 1.027–1.083 s | 1.41× |

All runs used workload hash `1de957c9976aa786d50cc0601532bb55ece766a8343d6b4cb72fdc986e1e2715`.
Eight and 12 workers performed similarly, with overlapping run ranges; these
measurements don't establish a meaningful difference between them. Sixteen
workers were slower on this workload. Results are machine-specific and aren't
a performance guarantee.

## Cache Builder

The cache JSON stores word-length and scoring compatibility metadata once per
file, while cache entries can be reused across different source dictionaries.
Individual rows retain their short `opening-word;clue-pattern` keys. Entries
whose suggested guess is not valid in the active dictionary are ignored.
Older cache entries are ignored after scoring changes; run `build_cache.py` to rebuild them.

`build_cache.py` evaluates the configured opening guesses across the full answer
set and writes second-guess data to `wordle_cache.json`. At the default
five-letter settings, this is a substantial batch job; the script uses
available CPUs and displays progress and an estimated time remaining. Building
the cache is optional and only helps runs that use cached second guesses.

It also reports each opening guess's average number of guesses across the
answer set.

Run it with:

```bash
python3 build_cache.py
```

It starts processing immediately rather than presenting an interactive prompt.
The cache is saved periodically, so interrupting the build may discard work
since the last save; rerun the command to continue filling missing entries.

## Repository Layout

- `wordle.py`: main entry point
- `argument_parser.py`, `config.py`: command-line parsing and shared configuration
- `wordle_gui.py`, `wordle_gui_layout.py`: Tkinter GUI and widget layout
- `game_logic.py`, `game_modes.py`, `logic.py`: gameplay flow and solver logic
- `algorithm.py`, `best_guess.py`, `second_guess.py`: guess scoring and cache-backed optimization
- `clues.py`, `clue_list.py`: clue representation, feedback, and candidate filtering
- `myconcurrent.py`, `mytypes.py`: worker-process management and shared type aliases
- `dictionary.py` and `*.txt`: dictionary inputs and curated answer/guess lists
- `build_cache.py`, `benchmark.py`: cache generation and solver benchmarking
- `spelling_bee_cheat.py`: standalone helper for NYT Spelling Bee, separate from the main Wordle solver flow
- `tests/`: automated tests
- `requirements.txt`, `requirements-dev.txt`: runtime and development dependencies
- `pytest.ini`, `.pylintrc`, `.github/workflows/ci.yml`: test, lint, and CI configuration

## Data Files

The default five-letter game is fully defined by the tracked curated word
lists. For other word lengths, the solver uses `/usr/share/dict/words` or
`/usr/share/dict/american-english`; install Ubuntu's `wamerican` package or
provide another source with `--dictionary`.

The generated cache file `wordle_cache.json` is also intentionally not tracked.

## License

This project is licensed under the GNU General Public License v3.0 or later. See [LICENSE](LICENSE).

## Author

Steve Gale
