# Connect Four Bot

Playground entrypoint:

```python
def make_move(board, player):
    ...
```

There are two bot implementations:

- **`main.py`** — Minimax alpha-beta with tuple-based board representation.
- **`bitboard_bot.py`** — Negamax alpha-beta with bitboard representation. Uses two integers for position/mask, bit-shift win checks, center-first ordering, iterative deepening, and a transposition table with EXACT/LOWER/UPPER bounds. Searches deeper than `main.py` within the same time budget.

Paste either file into the playground to play.

**Pyodide compatibility:** Do not include `if __name__ == "__main__"` blocks when pasting into the playground. Pyodide sets `__name__` to `"__main__"`, so that code would execute during initialization. Both bots also defensively convert the board with `int()` since Pyodide's `toPy` may pass proxy objects rather than native Python lists.

Run local checks:

```bash
python3 -m unittest discover -s tests
python3 harness.py --bot-a bot --bot-b random --games 20 --seed 1
```

`harness.py` can run any two named bots against each other:

```bash
python3 harness.py --bot-a bitboard --bot-b bot --games 20 --seed 1
python3 harness.py --bot-a bot --bot-b tactical --games 10 --time-limit 1.0
python3 harness.py --bot-a bot --bot-b bot --games 2 --show-games
```

Colors alternate by default so both bots get games as red and yellow. Use `--fixed-colors`
to keep bot A as red and bot B as yellow.

For search-based bots, the harness reports search depth, searched nodes, cache hit rate,
internal iterative-deepening timeouts, action mix, and remaining time-budget margin.
Both bots use an internal 0.85 second move budget to leave room under a 1.0 second
playground limit.

`main.py` converts the playground's `list[list[int]]` board into a compact row-major tuple
plus column heights before searching. Search uses last-move-aware win checks and tactical
move ordering to prune more of the tree.

`bitboard_bot.py` encodes the board as two integers (`position` for the current player's
pieces, `mask` for all pieces). Win detection uses bit shifts (horizontal=7, vertical=1,
diagonal=6/8). The negamax search eliminates separate max/min branches, and the
transposition table stores EXACT/LOWER/UPPER bounds for better node reuse.
