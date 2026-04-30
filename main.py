import time

ROWS = 6
COLS = 7
CONNECT = 4

CENTER_FIRST = (3, 2, 4, 1, 5, 0, 6)
WIN_SCORE = 1_000_000
MAX_CACHE_SIZE = 75_000
MOVE_TIME_LIMIT_SECONDS = 0.85

_LAST_SEARCH_STATS = {}


class _SearchTimeout(Exception):
    pass


def _build_win_lines():
    lines = []

    for row in range(ROWS):
        for col in range(COLS - CONNECT + 1):
            lines.append(tuple((row, col + offset) for offset in range(CONNECT)))

    for col in range(COLS):
        for row in range(ROWS - CONNECT + 1):
            lines.append(tuple((row + offset, col) for offset in range(CONNECT)))

    for row in range(ROWS - CONNECT + 1):
        for col in range(COLS - CONNECT + 1):
            lines.append(tuple((row + offset, col + offset) for offset in range(CONNECT)))

    for row in range(ROWS - CONNECT + 1):
        for col in range(CONNECT - 1, COLS):
            lines.append(tuple((row + offset, col - offset) for offset in range(CONNECT)))

    return tuple(lines)


WIN_LINES = _build_win_lines()


def get_last_search_stats():
    return dict(_LAST_SEARCH_STATS)


def make_move(board, player):
    """
    board  : list[list[int]] -- 6 rows x 7 cols
             0 = empty | 1/2 = players
             board[0] is the top row, board[5] is the bottom row
    player : int -- which player we are (1 or 2)
    return : int -- column to drop our piece into (0-6)
    """
    start = time.perf_counter()
    deadline = start + MOVE_TIME_LIMIT_SECONDS
    stats = _new_search_stats(board, player)

    valid_moves = _valid_moves(board)
    stats["valid_moves"] = len(valid_moves)

    if not valid_moves:
        _record_search_stats(stats, 0, "no_moves", start, deadline)
        return 0

    opponent = _other_player(player)

    # Take a win immediately.
    for col in _ordered_moves(valid_moves):
        next_board = _drop_piece(board, col, player)
        if _has_won(next_board, player):
            _record_search_stats(stats, col, "immediate_win", start, deadline)
            return col

    # Block an immediate loss.
    for col in _ordered_moves(valid_moves):
        next_board = _drop_piece(board, col, opponent)
        if _has_won(next_board, opponent):
            _record_search_stats(stats, col, "immediate_block", start, deadline)
            return col

    safe_moves = _safe_moves(board, valid_moves, player)
    search_moves = safe_moves or valid_moves
    stats["safe_moves"] = len(safe_moves)
    stats["candidate_moves"] = len(search_moves)

    max_depth = _max_search_depth(board)
    stats["max_depth"] = max_depth
    best_col = _choose_search_move(board, max_depth, search_moves, player, deadline, stats)

    if best_col in valid_moves:
        _record_search_stats(stats, best_col, "search", start, deadline)
        return best_col

    fallback = _ordered_moves(valid_moves)[0]
    _record_search_stats(stats, fallback, "fallback", start, deadline)
    return fallback


def _new_search_stats(board, player):
    return {
        "player": player,
        "pieces": sum(1 for row in board for cell in row if cell != 0),
        "valid_moves": 0,
        "safe_moves": 0,
        "candidate_moves": 0,
        "max_depth": 0,
        "depth_reached": 0,
        "best_score": None,
        "nodes": 0,
        "root_moves": 0,
        "cache_hits": 0,
        "cache_stores": 0,
        "cache_size": 0,
        "timed_out": False,
        "action": "",
        "selected_move": None,
        "elapsed_seconds": 0.0,
        "deadline_margin_seconds": 0.0,
    }


def _record_search_stats(stats, selected_move, action, start, deadline):
    global _LAST_SEARCH_STATS

    now = time.perf_counter()
    stats["action"] = action
    stats["selected_move"] = selected_move
    stats["elapsed_seconds"] = now - start
    stats["deadline_margin_seconds"] = deadline - now
    _LAST_SEARCH_STATS = dict(stats)


def _max_search_depth(board):
    pieces = sum(1 for row in board for cell in row if cell != 0)
    if pieces >= 28:
        return 9
    if pieces >= 14:
        return 7
    return 5


def _choose_search_move(board, max_depth, candidate_moves, player, deadline, stats):
    ordered = _ordered_moves(candidate_moves)
    if not ordered:
        return 0

    opponent = _other_player(player)
    cache = {}
    best_col = ordered[0]

    for depth in range(1, max_depth + 1):
        if _time_is_up(deadline):
            break

        try:
            score, col = _search_root(board, depth, ordered, opponent, player, cache, deadline, stats)
        except _SearchTimeout:
            stats["timed_out"] = True
            break

        if col in candidate_moves:
            best_col = col

        stats["depth_reached"] = depth
        stats["best_score"] = score
        stats["cache_size"] = len(cache)

        if abs(score) >= WIN_SCORE:
            break

    return best_col


def _search_root(board, depth, ordered_moves, next_player, root_player, cache, deadline, stats):
    best_score = -float("inf")
    best_col = ordered_moves[0]
    alpha = -float("inf")
    beta = float("inf")

    for col in ordered_moves:
        if _time_is_up(deadline):
            raise _SearchTimeout

        stats["root_moves"] += 1
        next_board = _drop_piece(board, col, root_player)
        score, _ = _minimax(next_board, depth - 1, alpha, beta, next_player, root_player, cache, deadline, stats)

        if score > best_score:
            best_score = score
            best_col = col

        alpha = max(alpha, best_score)

    return best_score, best_col


def _minimax(board, depth, alpha, beta, current_player, root_player, cache, deadline, stats):
    if _time_is_up(deadline):
        raise _SearchTimeout

    stats["nodes"] += 1

    cache_key = (_board_key(board), depth, current_player, root_player)
    cached = cache.get(cache_key)
    if cached is not None:
        stats["cache_hits"] += 1
        return cached

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
    exact_score = True

    if current_player == root_player:
        best_score = -float("inf")
        best_col = ordered[0]

        for col in ordered:
            next_board = _drop_piece(board, col, current_player)
            score, _ = _minimax(next_board, depth - 1, alpha, beta, next_player, root_player, cache, deadline, stats)

            if score > best_score:
                best_score = score
                best_col = col

            alpha = max(alpha, best_score)
            if alpha >= beta:
                exact_score = False
                break

        result = best_score, best_col
        if exact_score:
            _cache_result(cache, cache_key, result, stats)
        return result

    best_score = float("inf")
    best_col = ordered[0]

    for col in ordered:
        next_board = _drop_piece(board, col, current_player)
        score, _ = _minimax(next_board, depth - 1, alpha, beta, next_player, root_player, cache, deadline, stats)

        if score < best_score:
            best_score = score
            best_col = col

        beta = min(beta, best_score)
        if alpha >= beta:
            exact_score = False
            break

    result = best_score, best_col
    if exact_score:
        _cache_result(cache, cache_key, result, stats)
    return result


def _cache_result(cache, key, result, stats):
    if len(cache) >= MAX_CACHE_SIZE:
        return
    cache[key] = result
    stats["cache_stores"] += 1


def _time_is_up(deadline):
    return time.perf_counter() >= deadline


def _board_key(board):
    return tuple(tuple(row) for row in board)


def _valid_moves(board):
    return [col for col in range(COLS) if board[0][col] == 0]


def _ordered_moves(valid_moves):
    return [col for col in CENTER_FIRST if col in valid_moves]


def _safe_moves(board, valid_moves, player):
    opponent = _other_player(player)
    safe = []

    for col in valid_moves:
        next_board = _drop_piece(board, col, player)
        if not _winning_moves(next_board, opponent):
            safe.append(col)

    return safe


def _winning_moves(board, player):
    wins = []

    for col in _ordered_moves(_valid_moves(board)):
        next_board = _drop_piece(board, col, player)
        if _has_won(next_board, player):
            wins.append(col)

    return wins


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
    for line in WIN_LINES:
        if all(board[row][col] == player for row, col in line):
            return True
    return False


def _evaluate_board(board, player):
    opponent = _other_player(player)
    score = 0

    center_count = sum(1 for row in range(ROWS) if board[row][COLS // 2] == player)
    opponent_center_count = sum(1 for row in range(ROWS) if board[row][COLS // 2] == opponent)
    score += center_count * 6
    score -= opponent_center_count * 6

    player_wins = len(_winning_moves(board, player))
    opponent_wins = len(_winning_moves(board, opponent))
    score += player_wins * 4_000
    score -= opponent_wins * 5_000

    if player_wins >= 2:
        score += 20_000
    if opponent_wins >= 2:
        score -= 25_000

    for line in WIN_LINES:
        score += _score_line(board, line, player, opponent)

    return score


def _score_line(board, line, player, opponent):
    own_count = 0
    opponent_count = 0
    empty_count = 0

    for row, col in line:
        cell = board[row][col]
        if cell == player:
            own_count += 1
        elif cell == opponent:
            opponent_count += 1
        else:
            empty_count += 1

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
