# Connect Four Bot

Playground entrypoint:

```python
def make_move(board, player):
    ...
```

Paste `main.py` into the playground when testing the bot.

Run local checks:

```bash
python3 -m unittest discover -s tests
python3 harness.py --bot-a bot --bot-b random --games 20 --seed 1
```

`harness.py` can run any two named bots against each other:

```bash
python3 harness.py --bot-a bot --bot-b tactical --games 10 --time-limit 1.0
python3 harness.py --bot-a bot --bot-b bot --games 2 --show-games
```

Colors alternate by default so both bots get games as red and yellow. Use `--fixed-colors`
to keep bot A as red and bot B as yellow.

For the main bot, the harness also reports search depth, searched nodes, cache hit rate,
internal iterative-deepening timeouts, action mix, and remaining time-budget margin.
The bot uses an internal 0.85 second move budget to leave room under a 1.0 second
playground limit.
