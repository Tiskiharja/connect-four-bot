# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Connect Four bot designed for a playground environment. The bot implements iterative-deepening minimax with alpha-beta pruning under a strict 0.85s move budget (playground limit is 1.0s).

## Commands

```bash
# Run all tests
uv run python -m unittest discover -s tests

# Run a single test file
uv run python -m unittest tests.test_bot
uv run python -m unittest tests.test_harness

# Run harness simulations
uv run python harness.py --bot-a bot --bot-b random --games 20 --seed 1
uv run python harness.py --bot-a bot --bot-b tactical --games 10 --show-games
```

## Architecture

- **`main.py`** — The bot. Contains `make_move(board, player)` which is the playground entry point. Board is `list[list[int]]` (6x7, 0=empty, 1/2=players, row 0=top). Internally converts to a compact row-major tuple (`cells`) plus column `heights` tuple for faster search. Search flow: immediate win check → immediate block → filter safe moves → iterative-deepening minimax with alpha-beta pruning and transposition cache.

- **`harness.py`** — Local testing harness. Pits named bots (`bot`, `tactical`, `center`, `random`) against each other with configurable game count, seed, time limit, and color alternation. Reports search depth, node count, cache hit rate, and timing margins.

- **`tests/`** — unittest-based. `test_bot.py` tests the bot's core logic (win detection, move selection, time budget, search stats). `test_harness.py` tests the harness (illegal moves, crashes, timeouts, match tracking).

## Key constraints

- `make_move` must complete within 0.85s (`MOVE_TIME_LIMIT_SECONDS`). The playground enforces 1.0s.
- `main.py` must be self-contained — it gets pasted into the playground as-is. No external dependencies.
- The bot uses `_` prefixed functions (private by convention) that the harness and tests import directly.
- Python 3.12+, no third-party dependencies.
