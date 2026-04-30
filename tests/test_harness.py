import time
import unittest

from harness import play_game, run_matches


def invalid_bot(board, player):
    del board, player
    return 99


def crashing_bot(board, player):
    del board, player
    raise RuntimeError("boom")


def slow_bot(board, player):
    del board, player
    time.sleep(0.02)
    return 0


def first_valid_bot(board, player):
    del player
    return next(col for col in range(7) if board[0][col] == 0)


class HarnessTest(unittest.TestCase):
    def test_illegal_move_loses_game(self):
        result = play_game({1: invalid_bot, 2: first_valid_bot})

        self.assertEqual(result.winner, 2)
        self.assertIn("illegal move", result.reason)

    def test_crash_loses_game(self):
        result = play_game({1: crashing_bot, 2: first_valid_bot})

        self.assertEqual(result.winner, 2)
        self.assertIn("crash", result.reason)

    def test_timeout_loses_game(self):
        result = play_game({1: slow_bot, 2: first_valid_bot}, time_limit_seconds=0.001)

        self.assertEqual(result.winner, 2)
        self.assertIn("timeout", result.reason)

    def test_run_matches_tracks_both_bots(self):
        stats = run_matches("center", "random", games=2, seed=1, time_limit_seconds=1.0, alternate_colors=True)

        self.assertEqual(stats["a_wins"] + stats["b_wins"] + stats["draws"], 2)

    def test_run_matches_tracks_bot_search_metrics(self):
        stats = run_matches("bot", "random", games=1, seed=1, time_limit_seconds=1.0, alternate_colors=False)

        self.assertGreater(stats["a_search_count"], 0)
        self.assertGreater(stats["a_depth_total"], 0)
        self.assertGreater(stats["a_nodes_total"], 0)
        self.assertEqual(stats["b_search_count"], 0)


if __name__ == "__main__":
    unittest.main()
