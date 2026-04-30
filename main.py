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
WIN_LINE_INDEXES = tuple(
    tuple(row * COLS + col for row, col in line)
    for line in WIN_LINES
)
WIN_LINES_BY_INDEX = tuple(
    tuple(line for line in WIN_LINE_INDEXES if index in line)
    for index in range(ROWS * COLS)
)
CENTER_INDEXES = tuple(row * COLS + COLS // 2 for row in range(ROWS))


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
    cells, heights = _board_to_position(board)

    valid_moves = _position_valid_moves(heights)
    stats["valid_moves"] = len(valid_moves)

    if not valid_moves:
        _record_search_stats(stats, 0, "no_moves", start, deadline)
        return 0

    opponent = _other_player(player)

    # Take a win immediately.
    for col in _ordered_moves(valid_moves):
        next_cells, _, last_index = _position_drop_with_index(cells, heights, col, player)
        if _position_has_won_at(next_cells, player, last_index):
            _record_search_stats(stats, col, "immediate_win", start, deadline)
            return col

    # Block an immediate loss.
    for col in _ordered_moves(valid_moves):
        next_cells, _, last_index = _position_drop_with_index(cells, heights, col, opponent)
        if _position_has_won_at(next_cells, opponent, last_index):
            _record_search_stats(stats, col, "immediate_block", start, deadline)
            return col

    safe_moves = _position_safe_moves(cells, heights, valid_moves, player)
    search_moves = safe_moves or valid_moves
    stats["safe_moves"] = len(safe_moves)
    stats["candidate_moves"] = len(search_moves)

    best_col = _choose_search_move(cells, heights, ROWS * COLS, search_moves, player, deadline, stats)

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


def _choose_search_move(cells, heights, max_depth, candidate_moves, player, deadline, stats):
    ordered = _ordered_position_moves(cells, heights, candidate_moves, player, tactical=True)
    if not ordered:
        return 0

    opponent = _other_player(player)
    cache = {}
    best_col = ordered[0]
    start = time.perf_counter()

    for depth in range(1, max_depth + 1):
        now = time.perf_counter()
        remaining = deadline - now
        elapsed = now - start
        if remaining <= 0 or (depth > 1 and elapsed > 0.5 * remaining):
            break

        try:
            score, col = _search_root(cells, heights, depth, ordered, opponent, player, cache, deadline, stats)
        except _SearchTimeout:
            stats["timed_out"] = True
            break

        if col in candidate_moves:
            best_col = col
            if best_col != ordered[0]:
                ordered = [best_col] + [c for c in ordered if c != best_col]

        stats["depth_reached"] = depth
        stats["best_score"] = score
        stats["cache_size"] = len(cache)

        if abs(score) >= WIN_SCORE:
            break

    return best_col


def _search_root(cells, heights, depth, ordered_moves, next_player, root_player, cache, deadline, stats):
    best_score = -float("inf")
    best_col = ordered_moves[0]
    alpha = -float("inf")
    beta = float("inf")

    for col in ordered_moves:
        if _time_is_up(deadline):
            raise _SearchTimeout

        stats["root_moves"] += 1
        next_cells, next_heights, last_index = _position_drop_with_index(cells, heights, col, root_player)
        score, _ = _minimax(
            next_cells,
            next_heights,
            last_index,
            depth - 1,
            alpha,
            beta,
            next_player,
            root_player,
            cache,
            deadline,
            stats,
        )

        if score > best_score:
            best_score = score
            best_col = col

        alpha = max(alpha, best_score)

    return best_score, best_col


def _minimax(cells, heights, last_move_index, depth, alpha, beta, current_player, root_player, cache, deadline, stats):
    if _time_is_up(deadline):
        raise _SearchTimeout

    stats["nodes"] += 1

    cache_key = (cells, depth, current_player, root_player)
    cached = cache.get(cache_key)
    if cached is not None:
        stats["cache_hits"] += 1
        return cached

    valid_moves = _position_valid_moves(heights)
    previous_player = _other_player(current_player)

    if last_move_index is not None and _position_has_won_at(cells, previous_player, last_move_index):
        if previous_player == root_player:
            return WIN_SCORE + depth, None
        return -WIN_SCORE - depth, None

    if depth == 0 or not valid_moves:
        return _evaluate_position(cells, heights, root_player), None

    ordered = _ordered_position_moves(cells, heights, valid_moves, current_player, tactical=depth >= 2)
    next_player = _other_player(current_player)
    exact_score = True

    if current_player == root_player:
        best_score = -float("inf")
        best_col = ordered[0]

        for col in ordered:
            next_cells, next_heights, next_index = _position_drop_with_index(cells, heights, col, current_player)
            score, _ = _minimax(
                next_cells,
                next_heights,
                next_index,
                depth - 1,
                alpha,
                beta,
                next_player,
                root_player,
                cache,
                deadline,
                stats,
            )

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
        next_cells, next_heights, next_index = _position_drop_with_index(cells, heights, col, current_player)
        score, _ = _minimax(
            next_cells,
            next_heights,
            next_index,
            depth - 1,
            alpha,
            beta,
            next_player,
            root_player,
            cache,
            deadline,
            stats,
        )

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


def _board_to_position(board):
    cells = tuple(cell for row in board for cell in row)
    heights = tuple(sum(1 for row in range(ROWS) if board[row][col] != 0) for col in range(COLS))
    return cells, heights


def _position_valid_moves(heights):
    return [col for col in range(COLS) if heights[col] < ROWS]


def _position_drop(cells, heights, col, player):
    next_cells, next_heights, _ = _position_drop_with_index(cells, heights, col, player)
    return next_cells, next_heights


def _position_drop_with_index(cells, heights, col, player):
    row = ROWS - 1 - heights[col]
    index = row * COLS + col
    next_cells = cells[:index] + (player,) + cells[index + 1 :]
    next_heights = heights[:col] + (heights[col] + 1,) + heights[col + 1 :]
    return next_cells, next_heights, index


def _position_has_won(cells, player):
    for a, b, c, d in WIN_LINE_INDEXES:
        if cells[a] == player and cells[b] == player and cells[c] == player and cells[d] == player:
            return True
    return False


def _position_has_won_at(cells, player, index):
    for a, b, c, d in WIN_LINES_BY_INDEX[index]:
        if cells[a] == player and cells[b] == player and cells[c] == player and cells[d] == player:
            return True
    return False


def _position_safe_moves(cells, heights, valid_moves, player):
    opponent = _other_player(player)
    safe = []

    for col in valid_moves:
        next_cells, next_heights = _position_drop(cells, heights, col, player)
        if not _position_winning_moves(next_cells, next_heights, opponent):
            safe.append(col)

    return safe


def _position_winning_moves(cells, heights, player):
    wins = []

    for col in _ordered_moves(_position_valid_moves(heights)):
        next_cells, _, last_index = _position_drop_with_index(cells, heights, col, player)
        if _position_has_won_at(next_cells, player, last_index):
            wins.append(col)

    return wins


def _valid_moves(board):
    return [col for col in range(COLS) if board[0][col] == 0]


def _ordered_moves(valid_moves):
    return [col for col in CENTER_FIRST if col in valid_moves]


def _ordered_position_moves(cells, heights, valid_moves, player, tactical):
    ordered = _ordered_moves(valid_moves)
    if not tactical or len(ordered) <= 1:
        return ordered

    opponent = _other_player(player)
    ranked = []

    for fallback_rank, col in enumerate(ordered):
        next_cells, next_heights, last_index = _position_drop_with_index(cells, heights, col, player)
        score = 10 - abs((COLS // 2) - col)

        if _position_has_won_at(next_cells, player, last_index):
            score += 1_000_000
        else:
            own_wins = len(_position_winning_moves(next_cells, next_heights, player))
            opponent_wins = len(_position_winning_moves(next_cells, next_heights, opponent))

            if own_wins >= 2:
                score += 50_000
            elif own_wins == 1:
                score += 2_000

            if opponent_wins:
                score -= 100_000 + opponent_wins * 10_000

        ranked.append((score, -fallback_rank, col))

    ranked.sort(reverse=True)
    return [col for _, _, col in ranked]


def _safe_moves(board, valid_moves, player):
    cells, heights = _board_to_position(board)
    return _position_safe_moves(cells, heights, valid_moves, player)


def _winning_moves(board, player):
    cells, heights = _board_to_position(board)
    return _position_winning_moves(cells, heights, player)


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
    cells, heights = _board_to_position(board)
    return _evaluate_position(cells, heights, player)


def _evaluate_position(cells, heights, player):
    opponent = _other_player(player)
    score = 0

    center_count = sum(1 for index in CENTER_INDEXES if cells[index] == player)
    opponent_center_count = sum(1 for index in CENTER_INDEXES if cells[index] == opponent)
    score += center_count * 6
    score -= opponent_center_count * 6

    line_score, player_winning_cols, opponent_winning_cols = _score_lines_and_wins(
        cells,
        heights,
        player,
        opponent,
    )
    score += line_score

    player_wins = len(player_winning_cols)
    opponent_wins = len(opponent_winning_cols)
    score += player_wins * 4_000
    score -= opponent_wins * 5_000

    if player_wins >= 2:
        score += 20_000
    if opponent_wins >= 2:
        score -= 25_000

    return score


def _score_lines_and_wins(cells, heights, player, opponent):
    score = 0
    player_winning_cols = set()
    opponent_winning_cols = set()

    for line in WIN_LINE_INDEXES:
        line_score, player_win_col, opponent_win_col = _score_line(cells, heights, line, player, opponent)
        score += line_score

        if player_win_col is not None:
            player_winning_cols.add(player_win_col)
        if opponent_win_col is not None:
            opponent_winning_cols.add(opponent_win_col)

    return score, player_winning_cols, opponent_winning_cols


def _threat_summary(cells, heights, player):
    opponent = _other_player(player)
    summary = {
        "playable": 0,
        "near": 0,
        "floating": 0,
        "preferred_playable": 0,
        "preferred_near": 0,
        "playable_cols": set(),
    }

    for line in WIN_LINE_INDEXES:
        own_count = 0
        opponent_count = 0
        empty_count = 0
        empty_index = None

        for index in line:
            cell = cells[index]
            if cell == player:
                own_count += 1
            elif cell == opponent:
                opponent_count += 1
            else:
                empty_count += 1
                empty_index = index

        if own_count != 3 or opponent_count != 0 or empty_count != 1:
            continue

        distance = _empty_support_distance(empty_index, heights)
        _, col = divmod(empty_index, COLS)

        if distance == 0:
            summary["playable"] += 1
            summary["playable_cols"].add(col)
            if _is_preferred_threat_row(empty_index, player):
                summary["preferred_playable"] += 1
        elif distance == 1:
            summary["near"] += 1
            if _is_preferred_threat_row(empty_index, player):
                summary["preferred_near"] += 1
        else:
            summary["floating"] += 1

    return summary


def _empty_support_distance(index, heights):
    row, col = divmod(index, COLS)
    next_open_row = ROWS - 1 - heights[col]
    return max(0, next_open_row - row)


def _is_preferred_threat_row(index, player):
    row, _ = divmod(index, COLS)
    row_from_bottom = ROWS - row
    if player == 1:
        return row_from_bottom % 2 == 1
    return row_from_bottom % 2 == 0


def _score_line(cells, heights, line, player, opponent):
    own_count = 0
    opponent_count = 0
    empty_count = 0
    empty_index = None

    for index in line:
        cell = cells[index]
        if cell == player:
            own_count += 1
        elif cell == opponent:
            opponent_count += 1
        else:
            empty_count += 1
            empty_index = index

    if own_count == 4:
        return 100_000, None, None
    if opponent_count == 4:
        return -100_000, None, None
    if own_count == 3 and empty_count == 1:
        return 100, _playable_threat_col(empty_index, heights), None
    if own_count == 2 and empty_count == 2:
        return 10, None, None
    if own_count == 1 and empty_count == 3:
        return 1, None, None
    if opponent_count == 3 and empty_count == 1:
        return -120, None, _playable_threat_col(empty_index, heights)
    if opponent_count == 2 and empty_count == 2:
        return -12, None, None
    if opponent_count == 1 and empty_count == 3:
        return -1, None, None

    return 0, None, None


def _playable_threat_col(index, heights):
    if _empty_support_distance(index, heights) == 0:
        _, col = divmod(index, COLS)
        return col
    return None


def main():
    empty_board = [[0 for _ in range(COLS)] for _ in range(ROWS)]
    print(make_move(empty_board, 1))


if __name__ == "__main__":
    main()
