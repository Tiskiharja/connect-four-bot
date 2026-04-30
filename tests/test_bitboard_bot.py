import time
import unittest

from bitboard_bot import (
    COLS,
    MOVE_TIME_LIMIT_SECONDS,
    ROWS,
    TOP_BITS,
    _board_to_bitboard,
    _get_valid_columns,
    _is_winning,
    _make_move_bb,
    make_move,
)


def _empty_board():
    return [[0] * COLS for _ in range(ROWS)]


def _board_from_moves(moves, starting_player=1):
    board = _empty_board()
    player = starting_player
    for col in moves:
        for row in range(ROWS - 1, -1, -1):
            if board[row][col] == 0:
                board[row][col] = player
                break
        player = 3 - player
    return board


class TestBitboardConversion(unittest.TestCase):
    def test_empty_board(self):
        pos, mask, n = _board_to_bitboard(_empty_board(), 1)
        self.assertEqual(pos, 0)
        self.assertEqual(mask, 0)
        self.assertEqual(n, 0)

    def test_single_piece(self):
        board = _empty_board()
        board[5][3] = 1
        pos, mask, n = _board_to_bitboard(board, 1)
        expected_bit = 3 * 7 + 0
        self.assertEqual(pos, 1 << expected_bit)
        self.assertEqual(mask, 1 << expected_bit)
        self.assertEqual(n, 1)

    def test_two_players(self):
        board = _empty_board()
        board[5][3] = 1
        board[4][3] = 2
        pos, mask, n = _board_to_bitboard(board, 1)
        bit_bottom = 3 * 7 + 0
        bit_above = 3 * 7 + 1
        self.assertEqual(pos, 1 << bit_bottom)
        self.assertEqual(mask, (1 << bit_bottom) | (1 << bit_above))
        self.assertEqual(n, 2)


class TestWinDetection(unittest.TestCase):
    def test_horizontal_win(self):
        pos = 0
        for c in range(4):
            pos |= 1 << (c * 7 + 0)
        self.assertTrue(_is_winning(pos))

    def test_vertical_win(self):
        pos = 0
        for r in range(4):
            pos |= 1 << (0 * 7 + r)
        self.assertTrue(_is_winning(pos))

    def test_diagonal_ascending_win(self):
        pos = 0
        for d in range(4):
            pos |= 1 << (d * 7 + d)
        self.assertTrue(_is_winning(pos))

    def test_diagonal_descending_win(self):
        pos = 0
        for d in range(4):
            pos |= 1 << (d * 7 + (3 - d))
        self.assertTrue(_is_winning(pos))

    def test_three_not_winning(self):
        pos = 0
        for c in range(3):
            pos |= 1 << (c * 7 + 0)
        self.assertFalse(_is_winning(pos))


class TestMakeMoveBB(unittest.TestCase):
    def test_perspective_swap(self):
        board = _empty_board()
        board[5][3] = 1
        pos, mask, _ = _board_to_bitboard(board, 1)
        new_pos, new_mask = _make_move_bb(pos, mask, 0)

        p1_bit = 3 * 7
        new_bit = 0 * 7
        # new_pos = pos ^ mask = P2's pieces = 0 (correct - no P2 pieces yet)
        self.assertEqual(new_pos, 0)
        # new_mask has both pieces
        self.assertEqual(new_mask, (1 << p1_bit) | (1 << new_bit))
        # opponent_pos (previous player who just placed) = new_pos ^ new_mask
        opponent_pos = new_pos ^ new_mask
        # Should be P1's pieces INCLUDING the just-placed piece
        self.assertEqual(opponent_pos, (1 << p1_bit) | (1 << new_bit))

    def test_win_detection_after_move(self):
        # P1 has 3 in a row at bottom: cols 0,1,2. Place at col 3 to win.
        board = _board_from_moves([0, 6, 1, 6, 2, 6])
        pos, mask, _ = _board_to_bitboard(board, 1)
        new_pos, new_mask = _make_move_bb(pos, mask, 3)
        # Check that the previous player (P1) won
        opponent_pos = new_pos ^ new_mask
        self.assertTrue(_is_winning(opponent_pos))


class TestMakeMove(unittest.TestCase):
    def test_empty_board_prefers_center(self):
        self.assertEqual(make_move(_empty_board(), 1), 3)

    def test_takes_immediate_win_horizontal(self):
        board = _board_from_moves([0, 6, 1, 6, 2, 6])
        self.assertEqual(make_move(board, 1), 3)

    def test_takes_immediate_win_vertical(self):
        board = _board_from_moves([0, 6, 0, 6, 0, 6])
        self.assertEqual(make_move(board, 1), 0)

    def test_blocks_immediate_loss(self):
        # P2 has bottom of cols 3,4,5. P1 must block at col 2 or 6.
        board = _board_from_moves([0, 3, 1, 4, 6, 5])
        col = make_move(board, 1)
        # P2 wins at (5,2) horizontally. Col 6 bottom is taken by P1.
        self.assertEqual(col, 2)

    def test_does_not_mutate_board(self):
        board = _empty_board()
        board_copy = [row[:] for row in board]
        make_move(board, 1)
        self.assertEqual(board, board_copy)

    def test_returns_valid_column(self):
        col = make_move(_empty_board(), 1)
        self.assertIn(col, range(COLS))

    def test_time_budget(self):
        start = time.perf_counter()
        make_move(_empty_board(), 1)
        elapsed = time.perf_counter() - start
        self.assertLess(elapsed, MOVE_TIME_LIMIT_SECONDS + 0.1)


class TestValidColumns(unittest.TestCase):
    def test_empty_board(self):
        cols = _get_valid_columns(0)
        self.assertEqual(cols, [3, 2, 4, 1, 5, 0, 6])

    def test_full_column(self):
        mask = 0
        for r in range(ROWS):
            mask |= 1 << (3 * 7 + r)
        cols = _get_valid_columns(mask)
        self.assertNotIn(3, cols)
        self.assertEqual(len(cols), 6)


if __name__ == "__main__":
    unittest.main()
