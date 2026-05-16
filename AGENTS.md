# AGENTS.md

Guidance for coding agents and contributors working in this repository.

## Project Overview

This is a Python Wordle solver/play tool with:

- a CLI entry point in `wordle.py`
- a Tkinter GUI in `wordle_gui.py`
- solver, scoring, and gameplay logic split across small modules
- pytest coverage in `tests/`

The codebase is flat rather than package-based, so most imports are from sibling files in the repo root.

## Environment

- Python 3.12 or newer is recommended
- Runtime dependencies: `colorama`, `psutil`
- Dev/test dependencies are in `requirements-dev.txt`

Common setup:

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Common Commands

Run the CLI:

```bash
python3 wordle.py
```

Launch the GUI:

```bash
python3 wordle.py --gui
```

Run tests:

```bash
pytest
```

Build the cache:

```bash
python3 build_cache.py
```

## Repository Map

- `wordle.py`: main entry point and argument wiring
- `argument_parser.py`: CLI argument definitions
- `wordle_gui.py`: Tkinter application
- `game_logic.py`, `game_modes.py`, `logic.py`: gameplay and solver flow
- `algorithm.py`, `best_guess.py`, `second_guess.py`: guess scoring and optimization
- `dictionary.py`: dictionary loading and filtering
- `clues.py`, `clue_list.py`: clue handling
- `config.py`: shared configuration
- `tests/`: pytest coverage for the main modules

## Editing Guidelines

- Keep changes narrow and consistent with the existing single-module layout
- Prefer updating or adding pytest coverage when behavior changes
- Preserve CLI behavior unless the task explicitly requires interface changes
- Treat the GUI as optional functionality; avoid breaking CLI-only environments
- Keep text word lists and curated answer files in plain newline-delimited form
- Keep execution performance in mind when making changes

## Data and Generated Files

- Dictionary and answer data live in `*.txt` files in the repo root
- `american-english` is local data derived from the Ubuntu `wamerican` source
- Cache output such as `wordle_cache.json` is generated data and should not be hand-edited
- Backup or historical files such as `*.bak`, `*_old.py`, and `*~` should not be used as implementation targets unless a task explicitly calls for it

## Testing Expectations

- Run `pytest` after code changes when feasible
- If a change touches solver logic, favor targeted regression coverage in `tests/`
- If GUI behavior changes, verify the CLI test suite still passes even if the GUI is not exercised interactively

## Notes for Agents

- Search with `rg` for fast codebase discovery
- Check for existing tests before adding new helpers or abstractions
- Because modules are imported directly from the repo root, avoid reorganizing files unless the task specifically requires a structural refactor
