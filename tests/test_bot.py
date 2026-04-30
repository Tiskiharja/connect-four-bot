import unittest

from main import COLS, ROWS, _drop_piece, _has_won, _safe_moves, make_move


def empty_board():
    return [[0 for _ in range(COLS)] for _ in range(ROWS)]


class ConnectFourBotTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
