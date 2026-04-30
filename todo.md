 Findings

  1. main.py:145: _max_search_depth is the biggest strength limiter. Empty board reaches depth 6 in ~0.11s, leaving ~0.74s unused. Let iterative deepening continue until the deadline, or raise the cap dynamically.
  2. main.py:341: each simulated drop allocates new tuples via slicing. That is clean, but expensive at scale. A bitboard representation would likely buy the most extra depth under a 1s budget.
  3. main.py:394: tactical move ordering is useful, but it calls _position_winning_moves for both players per candidate, which becomes expensive inside the tree. Consider using the heavy tactical ordering only at
     root / shallow depths, or cache those local winning-move checks.
  4. main.py:508: _threat_summary and parity helpers exist but are not used by _evaluate_position. Folding preferred odd/even threats, near threats, and double threats into main.py:461 should improve horizon
     decisions.
  5. main.py:226: the transposition cache only stores exact no-cutoff results. A real TT with EXACT, LOWER, UPPER, depth, and best move would improve both pruning and move ordering.

  Best Next Improvement
  Keep the current bot, but change the search loop to run iterative deepening until time instead of stopping at fixed depth 6/7/8. Add previous-iteration best move first at the root. This is low-risk and directly
  uses the unused budget.

  Alternative Worth Testing
  Implement a bitboard negamax alpha-beta bot and test it against this one. Use two integers for position/mask, bit-shift win checks, center-first ordering, iterative deepening to ~0.90s, and a transposition table.
  For Connect Four, this is usually a better 1-second approach than MCTS because the branching factor is small and tactical exact search matters.

  Checks Run
  python3 -m unittest discover -s tests: 23 tests passed.

  Harness samples:

  - bot vs random, 100 games: 100-0, no timeouts, avg/max move 0.1379s / 0.7819s.
  - bot vs tactical, 100 games: 100-0, no timeouts, avg/max move 0.0917s / 0.4882s.
  - bot vs bot, 4 games: no external timeouts, but internal search hit the 0.85s deadline several times, so deeper search should keep the safety margin.