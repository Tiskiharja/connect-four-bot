ROWS = 6
COLS = 7
CONNECT = 4

CENTER_FIRST = (3, 2, 4, 1, 5, 0, 6)
WIN_SCORE = 1_000_000


def make_move(board, player):
    """
    board  : list[list[int]] -- 6 rows x 7 cols
             0 = empty | 1/2 = players
             board[0] is the top row, board[5] is the bottom row
    player : int -- which player we are (1 or 2)
    return : int -- column to drop our piece into (0-6)
    """
    valid_moves = _valid_moves(board)
    if not valid_moves:
        return 0

    opponent = _other_player(player)

    # Take a win immediately.
    for col in _ordered_moves(valid_moves):
        next_board = _drop_piece(board, col, player)
        if _has_won(next_board, player):
            return col

    # Block an immediate loss.
    for col in _ordered_moves(valid_moves):
        next_board = _drop_piece(board, col, opponent)
        if _has_won(next_board, opponent):
            return col

    depth = _search_depth(board)
    _, best_col = _minimax(board, depth, -float("inf"), float("inf"), player, player)

    if best_col in valid_moves:
        return best_col
    return _ordered_moves(valid_moves)[0]


def _search_depth(board):
    pieces = sum(1 for row in board for cell in row if cell != 0)
    if pieces >= 30:
        return 6
    if pieces >= 16:
        return 5
    return 4


def _minimax(board, depth, alpha, beta, current_player, root_player):
    valid_moves = _valid_moves(board)
    root_opponent = _other_player(root_player)

    if _has_won(board, root_player):
        return WIN_SCORE + depth, None
    if _has_won(board, root_opponent):
        return -WIN_SCORE - depth, None
    if depth == 0 or not valid_moves:
        return _evaluate_board(board, root_player), None

    ordered = _ordered_moves(valid_moves)
    next_player = _other_player(current_player)

    if current_player == root_player:
        best_score = -float("inf")
        best_col = ordered[0]

        for col in ordered:
            next_board = _drop_piece(board, col, current_player)
            score, _ = _minimax(next_board, depth - 1, alpha, beta, next_player, root_player)

            if score > best_score:
                best_score = score
                best_col = col

            alpha = max(alpha, best_score)
            if alpha >= beta:
                break

        return best_score, best_col

    best_score = float("inf")
    best_col = ordered[0]

    for col in ordered:
        next_board = _drop_piece(board, col, current_player)
        score, _ = _minimax(next_board, depth - 1, alpha, beta, next_player, root_player)

        if score < best_score:
            best_score = score
            best_col = col

        beta = min(beta, best_score)
        if alpha >= beta:
            break

    return best_score, best_col


def _valid_moves(board):
    return [col for col in range(COLS) if board[0][col] == 0]


def _ordered_moves(valid_moves):
    return [col for col in CENTER_FIRST if col in valid_moves]


def _drop_piece(board, col, player):
    next_board = [row[:] for row in board]
    for row in range(ROWS - 1, -1, -1):
        if next_board[row][col] == 0:
            next_board[row][col] = player
            return next_board
    return next_board


def _other_player(player):
    return 3 - player


def _has_won(board, player):
    for row in range(ROWS):
        for col in range(COLS):
            if board[row][col] != player:
                continue

            if (
                _count_direction(board, row, col, 0, 1, player) >= CONNECT
                or _count_direction(board, row, col, 1, 0, player) >= CONNECT
                or _count_direction(board, row, col, 1, 1, player) >= CONNECT
                or _count_direction(board, row, col, 1, -1, player) >= CONNECT
            ):
                return True

    return False


def _count_direction(board, start_row, start_col, row_step, col_step, player):
    count = 0
    row = start_row
    col = start_col

    while 0 <= row < ROWS and 0 <= col < COLS and board[row][col] == player:
        count += 1
        row += row_step
        col += col_step

    return count


def _evaluate_board(board, player):
    opponent = _other_player(player)
    score = 0

    center_count = sum(1 for row in range(ROWS) if board[row][COLS // 2] == player)
    opponent_center_count = sum(1 for row in range(ROWS) if board[row][COLS // 2] == opponent)
    score += center_count * 6
    score -= opponent_center_count * 6

    for window in _windows(board):
        score += _score_window(window, player)

    return score


def _windows(board):
    for row in range(ROWS):
        for col in range(COLS - CONNECT + 1):
            yield [board[row][col + offset] for offset in range(CONNECT)]

    for col in range(COLS):
        for row in range(ROWS - CONNECT + 1):
            yield [board[row + offset][col] for offset in range(CONNECT)]

    for row in range(ROWS - CONNECT + 1):
        for col in range(COLS - CONNECT + 1):
            yield [board[row + offset][col + offset] for offset in range(CONNECT)]

    for row in range(ROWS - CONNECT + 1):
        for col in range(CONNECT - 1, COLS):
            yield [board[row + offset][col - offset] for offset in range(CONNECT)]


def _score_window(window, player):
    opponent = _other_player(player)
    own_count = window.count(player)
    opponent_count = window.count(opponent)
    empty_count = window.count(0)

    if own_count == 4:
        return 100_000
    if opponent_count == 4:
        return -100_000
    if own_count == 3 and empty_count == 1:
        return 100
    if own_count == 2 and empty_count == 2:
        return 10
    if own_count == 1 and empty_count == 3:
        return 1
    if opponent_count == 3 and empty_count == 1:
        return -120
    if opponent_count == 2 and empty_count == 2:
        return -12
    if opponent_count == 1 and empty_count == 3:
        return -1

    return 0


def main():
    empty_board = [[0 for _ in range(COLS)] for _ in range(ROWS)]
    print(make_move(empty_board, 1))


if __name__ == "__main__":
    main()
