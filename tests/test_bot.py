import unittest
import time

from main import (
    COLS,
    MOVE_TIME_LIMIT_SECONDS,
    ROWS,
    WIN_LINES_BY_INDEX,
    WIN_LINE_INDEXES,
    WIN_LINES,
    _board_to_position,
    _drop_piece,
    _empty_support_distance,
    _evaluate_board,
    _has_won,
    _ordered_position_moves,
    _position_drop,
    _position_drop_with_index,
    _position_has_won,
    _position_has_won_at,
    _position_valid_moves,
    _safe_moves,
    _threat_summary,
    get_last_search_stats,
    make_move,
)


def empty_board():
    return [[0 for _ in range(COLS)] for _ in range(ROWS)]


def _valid_columns(board):
    return [col for col in range(COLS) if board[0][col] == 0]


class ConnectFourBotTest(unittest.TestCase):
    def test_precomputes_classic_board_win_lines(self):
        self.assertEqual(len(WIN_LINES), 69)
        self.assertEqual(len(set(WIN_LINES)), 69)
        self.assertEqual(len(WIN_LINE_INDEXES), 69)
        self.assertEqual(len(set(WIN_LINE_INDEXES)), 69)
        self.assertEqual(len(WIN_LINES_BY_INDEX), ROWS * COLS)
        self.assertTrue(all(WIN_LINES_BY_INDEX))

    def test_compact_position_matches_board_drop(self):
        board = empty_board()
        board[5][3] = 1
        cells, heights = _board_to_position(board)

        next_board = _drop_piece(board, 3, 2)
        next_cells, next_heights, last_index = _position_drop_with_index(cells, heights, 3, 2)

        self.assertEqual(next_cells, tuple(cell for row in next_board for cell in row))
        self.assertEqual(next_heights[3], 2)
        self.assertEqual(last_index, 4 * COLS + 3)
        self.assertEqual(_position_valid_moves(next_heights), _valid_columns(next_board))

    def test_compact_position_detects_win(self):
        board = empty_board()
        board[5][0] = 1
        board[5][1] = 1
        board[5][2] = 1
        board[5][3] = 1
        cells, _ = _board_to_position(board)

        self.assertTrue(_has_won(board, 1))
        self.assertTrue(_position_has_won(cells, 1))
        self.assertTrue(_position_has_won_at(cells, 1, 5 * COLS + 3))

    def test_threat_summary_distinguishes_playable_threat(self):
        board = empty_board()
        board[5][0] = 1
        board[5][1] = 1
        board[5][2] = 1
        cells, heights = _board_to_position(board)
        threat_index = 5 * COLS + 3

        summary = _threat_summary(cells, heights, 1)

        self.assertEqual(_empty_support_distance(threat_index, heights), 0)
        self.assertIn(3, summary["playable_cols"])
        self.assertGreaterEqual(summary["playable"], 1)

    def test_threat_summary_distinguishes_near_threat(self):
        board = empty_board()
        board[5][0] = 2
        board[5][1] = 2
        board[5][2] = 2
        board[4][0] = 1
        board[4][1] = 1
        board[4][2] = 1
        cells, heights = _board_to_position(board)
        threat_index = 4 * COLS + 3

        summary = _threat_summary(cells, heights, 1)

        self.assertEqual(_empty_support_distance(threat_index, heights), 1)
        self.assertNotIn(3, summary["playable_cols"])
        self.assertGreaterEqual(summary["near"], 1)

    def test_evaluator_values_playable_threat_more_than_near_threat(self):
        playable = empty_board()
        playable[5][0] = 1
        playable[5][1] = 1
        playable[5][2] = 1

        near = empty_board()
        near[5][0] = 2
        near[5][1] = 2
        near[5][2] = 2
        near[4][0] = 1
        near[4][1] = 1
        near[4][2] = 1

        self.assertGreater(_evaluate_board(playable, 1), _evaluate_board(near, 1))

    def test_empty_board_prefers_center(self):
        self.assertEqual(make_move(empty_board(), 1), 3)

    def test_returns_valid_move(self):
        board = empty_board()
        board[5][3] = 1
        board[4][3] = 2

        self.assertIn(make_move(board, 1), range(COLS))

    def test_does_not_mutate_board(self):
        board = empty_board()
        board[5][0] = 1
        original = [row[:] for row in board]

        make_move(board, 2)

        self.assertEqual(board, original)

    def test_takes_immediate_horizontal_win(self):
        board = empty_board()
        board[5][0] = 1
        board[5][1] = 1
        board[5][2] = 1

        self.assertEqual(make_move(board, 1), 3)

    def test_blocks_immediate_horizontal_loss(self):
        board = empty_board()
        board[5][0] = 2
        board[5][1] = 2
        board[5][2] = 2

        self.assertEqual(make_move(board, 1), 3)

    def test_takes_immediate_vertical_win(self):
        board = empty_board()
        board[5][4] = 1
        board[4][4] = 1
        board[3][4] = 1

        self.assertEqual(make_move(board, 1), 4)

    def test_detects_diagonal_win_after_drop(self):
        board = empty_board()
        board[5][0] = 1
        board[5][1] = 2
        board[4][1] = 1
        board[5][2] = 2
        board[4][2] = 2
        board[3][2] = 1
        board[5][3] = 2
        board[4][3] = 2
        board[3][3] = 2

        next_board = _drop_piece(board, 3, 1)

        self.assertTrue(_has_won(next_board, 1))

    def test_avoids_move_that_creates_immediate_opponent_win(self):
        board = empty_board()
        board[5][0] = 1
        board[5][1] = 1
        board[5][2] = 2
        board[4][0] = 2
        board[4][1] = 2
        board[4][2] = 2

        self.assertNotIn(3, _safe_moves(board, list(range(COLS)), 1))
        self.assertNotEqual(make_move(board, 1), 3)

    def test_tactical_ordering_prioritizes_winning_move(self):
        board = empty_board()
        board[5][0] = 1
        board[5][1] = 1
        board[5][2] = 1
        cells, heights = _board_to_position(board)

        ordered = _ordered_position_moves(cells, heights, list(range(COLS)), 1, tactical=True)

        self.assertEqual(ordered[0], 3)

    def test_move_stays_under_one_second_budget(self):
        start = time.perf_counter()
        move = make_move(empty_board(), 1)
        elapsed = time.perf_counter() - start

        self.assertEqual(move, 3)
        self.assertLess(elapsed, MOVE_TIME_LIMIT_SECONDS + 0.10)

    def test_records_search_stats(self):
        move = make_move(empty_board(), 1)
        stats = get_last_search_stats()

        self.assertEqual(stats["selected_move"], move)
        self.assertEqual(stats["action"], "search")
        self.assertGreater(stats["depth_reached"], 0)
        self.assertGreater(stats["nodes"], 0)
        self.assertIn("elapsed_seconds", stats)

    def test_records_immediate_action_stats(self):
        board = empty_board()
        board[5][0] = 1
        board[5][1] = 1
        board[5][2] = 1

        move = make_move(board, 1)
        stats = get_last_search_stats()

        self.assertEqual(move, 3)
        self.assertEqual(stats["selected_move"], 3)
        self.assertEqual(stats["action"], "immediate_win")
        self.assertEqual(stats["depth_reached"], 0)


if __name__ == "__main__":
    unittest.main()
