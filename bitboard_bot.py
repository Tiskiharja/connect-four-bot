import time

ROWS = 6
COLS = 7

MOVE_TIME_LIMIT_SECONDS = 0.85
WIN_SCORE = 1_000_000
MAX_CACHE_SIZE = 200_000

CENTER_FIRST = (3, 2, 4, 1, 5, 0, 6)

# Bitboard layout: column c occupies bits [c*7 .. c*7+6]
# bit c*7 = bottom of column, c*7+5 = top playable, c*7+6 = sentinel
BOTTOM_BITS = tuple(1 << (c * 7) for c in range(COLS))
TOP_BITS = tuple(1 << (c * 7 + ROWS - 1) for c in range(COLS))
COLUMN_MASKS = tuple(((1 << ROWS) - 1) << (c * 7) for c in range(COLS))
BOARD_MASK = 0
for _c in range(COLS):
    BOARD_MASK |= COLUMN_MASKS[_c]

# Transposition table flags
FLAG_EXACT = 0
FLAG_LOWER = 1
FLAG_UPPER = 2

_LAST_SEARCH_STATS = {}


class _SearchTimeout(Exception):
    pass


def _build_line_masks():
    lines = []
    # Horizontal
    for row in range(ROWS):
        for col in range(COLS - 3):
            mask = 0
            for dc in range(4):
                mask |= 1 << ((col + dc) * 7 + row)
            lines.append(mask)
    # Vertical
    for col in range(COLS):
        for row in range(ROWS - 3):
            mask = 0
            for dr in range(4):
                mask |= 1 << (col * 7 + row + dr)
            lines.append(mask)
    # Diagonal / (ascending)
    for col in range(COLS - 3):
        for row in range(ROWS - 3):
            mask = 0
            for d in range(4):
                mask |= 1 << ((col + d) * 7 + row + d)
            lines.append(mask)
    # Diagonal \ (descending)
    for col in range(COLS - 3):
        for row in range(3, ROWS):
            mask = 0
            for d in range(4):
                mask |= 1 << ((col + d) * 7 + row - d)
            lines.append(mask)
    return tuple(lines)


LINE_MASKS = _build_line_masks()


def get_last_search_stats():
    return dict(_LAST_SEARCH_STATS)


def make_move(board, player):
    start = time.perf_counter()
    deadline = start + MOVE_TIME_LIMIT_SECONDS
    position, mask, num_moves = _board_to_bitboard(board, player)
    stats = _new_stats(num_moves, player)

    valid_cols = _get_valid_columns(mask)
    if not valid_cols:
        _record_stats(stats, 0, "no_moves", start, deadline)
        return 0

    # Take a win immediately.
    for col in valid_cols:
        new_pos, new_mask = _make_move_bb(position, mask, col)
        # Check if current player (whose pieces are in `position`) just won.
        # The placed bit is (mask + BOTTOM_BITS[col]) & COLUMN_MASKS[col], added to position.
        placed = position | ((mask + BOTTOM_BITS[col]) & COLUMN_MASKS[col])
        if _is_winning(placed):
            _record_stats(stats, col, "immediate_win", start, deadline)
            return col

    # Block an immediate loss.
    opponent = position ^ mask
    blocking_cols = []
    for col in valid_cols:
        opp_placed = opponent | ((mask + BOTTOM_BITS[col]) & COLUMN_MASKS[col])
        if _is_winning(opp_placed):
            blocking_cols.append(col)

    if len(blocking_cols) == 1:
        _record_stats(stats, blocking_cols[0], "immediate_block", start, deadline)
        return blocking_cols[0]
    if len(blocking_cols) > 1:
        # Multiple threats — likely lost, but block one
        _record_stats(stats, blocking_cols[0], "immediate_block", start, deadline)
        return blocking_cols[0]

    best_col = _iterative_deepening(position, mask, num_moves, valid_cols, deadline, stats)

    if best_col in valid_cols:
        _record_stats(stats, best_col, "search", start, deadline)
        return best_col

    fallback = valid_cols[0]
    _record_stats(stats, fallback, "fallback", start, deadline)
    return fallback


def _board_to_bitboard(board, player):
    position = 0
    mask = 0
    num_moves = 0
    for col in range(COLS):
        for row in range(ROWS):
            if board[row][col] != 0:
                bit = col * 7 + (ROWS - 1 - row)
                mask |= 1 << bit
                if board[row][col] == player:
                    position |= 1 << bit
                num_moves += 1
    return position, mask, num_moves


def _can_play(mask, col):
    return (mask & TOP_BITS[col]) == 0


def _get_valid_columns(mask):
    return [col for col in CENTER_FIRST if _can_play(mask, col)]


def _make_move_bb(position, mask, col):
    new_position = position ^ mask  # swap perspective FIRST (opponent's pieces)
    new_mask = mask | ((mask + BOTTOM_BITS[col]) & COLUMN_MASKS[col])  # then add piece
    return new_position, new_mask


def _is_winning(position):
    # Horizontal (shift by 7 = one column apart)
    m = position & (position >> 7)
    if m & (m >> 14):
        return True
    # Vertical (shift by 1 = one row within column)
    m = position & (position >> 1)
    if m & (m >> 2):
        return True
    # Diagonal \ (shift by 6)
    m = position & (position >> 6)
    if m & (m >> 12):
        return True
    # Diagonal / (shift by 8)
    m = position & (position >> 8)
    if m & (m >> 16):
        return True
    return False


def _iterative_deepening(position, mask, num_moves, valid_cols, deadline, stats):
    if not valid_cols:
        return 0

    best_col = valid_cols[0]
    tt = {}
    max_possible_depth = ROWS * COLS - num_moves
    ordered = list(valid_cols)
    start = time.perf_counter()

    for depth in range(1, max_possible_depth + 1):
        now = time.perf_counter()
        remaining = deadline - now
        elapsed = now - start
        if remaining <= 0 or (depth > 1 and elapsed > 0.5 * remaining):
            break

        try:
            score, col = _search_root(position, mask, num_moves, depth, ordered, tt, deadline, stats)
        except _SearchTimeout:
            stats["timed_out"] = True
            break

        if col is not None and col in valid_cols:
            best_col = col
            if best_col != ordered[0]:
                ordered = [best_col] + [c for c in ordered if c != best_col]

        stats["depth_reached"] = depth
        stats["best_score"] = score
        stats["cache_size"] = len(tt)

        if abs(score) >= WIN_SCORE:
            break

    return best_col


def _search_root(position, mask, num_moves, depth, ordered_cols, tt, deadline, stats):
    best_score = -float("inf")
    best_col = ordered_cols[0]
    alpha = -float("inf")
    beta = float("inf")

    for col in ordered_cols:
        if time.perf_counter() >= deadline:
            raise _SearchTimeout

        stats["root_moves"] += 1

        # Check if this move wins
        placed = position | ((mask + BOTTOM_BITS[col]) & COLUMN_MASKS[col])
        if _is_winning(placed):
            return WIN_SCORE + (ROWS * COLS - num_moves), col

        new_pos, new_mask = _make_move_bb(position, mask, col)
        score = -_negamax(new_pos, new_mask, num_moves + 1, depth - 1, -beta, -alpha, tt, deadline, stats)

        if score > best_score:
            best_score = score
            best_col = col
        alpha = max(alpha, score)

    return best_score, best_col


def _negamax(position, mask, num_moves, depth, alpha, beta, tt, deadline, stats):
    if time.perf_counter() >= deadline:
        raise _SearchTimeout

    stats["nodes"] += 1

    # The previous player just moved. Their pieces = position ^ mask (after perspective swap).
    opponent_pos = position ^ mask
    if _is_winning(opponent_pos):
        return -(WIN_SCORE + (ROWS * COLS - num_moves))

    # Draw
    if num_moves >= ROWS * COLS:
        return 0

    if depth <= 0:
        return _evaluate_bb(position, mask)

    # Transposition table lookup
    key = (position, mask)
    entry = tt.get(key)
    tt_best = None
    if entry is not None:
        tt_score, tt_flag, tt_depth, tt_best = entry
        if tt_depth >= depth:
            stats["cache_hits"] += 1
            if tt_flag == FLAG_EXACT:
                return tt_score
            elif tt_flag == FLAG_LOWER:
                alpha = max(alpha, tt_score)
            elif tt_flag == FLAG_UPPER:
                beta = min(beta, tt_score)
            if alpha >= beta:
                return tt_score

    valid_cols = _get_valid_columns(mask)
    if not valid_cols:
        return 0

    # Move ordering: TT best move first, then center-first (already the default order)
    if tt_best is not None and tt_best in valid_cols and tt_best != valid_cols[0]:
        valid_cols = [tt_best] + [c for c in valid_cols if c != tt_best]

    best_score = -float("inf")
    best_col = valid_cols[0]
    original_alpha = alpha

    for col in valid_cols:
        new_pos, new_mask = _make_move_bb(position, mask, col)
        score = -_negamax(new_pos, new_mask, num_moves + 1, depth - 1, -beta, -alpha, tt, deadline, stats)

        if score > best_score:
            best_score = score
            best_col = col
        alpha = max(alpha, score)
        if alpha >= beta:
            break

    # Store in transposition table
    if len(tt) < MAX_CACHE_SIZE:
        if best_score <= original_alpha:
            flag = FLAG_UPPER
        elif best_score >= beta:
            flag = FLAG_LOWER
        else:
            flag = FLAG_EXACT
        tt[key] = (best_score, flag, depth, best_col)
        stats["cache_stores"] += 1

    return best_score


def _evaluate_bb(position, mask):
    opponent = position ^ mask
    score = 0

    for line_mask in LINE_MASKS:
        own = bin(position & line_mask).count('1')
        opp = bin(opponent & line_mask).count('1')
        if opp == 0:
            if own == 3:
                score += 100
            elif own == 2:
                score += 10
            elif own == 1:
                score += 1
        elif own == 0:
            if opp == 3:
                score -= 120
            elif opp == 2:
                score -= 12
            elif opp == 1:
                score -= 1

    # Center column bonus
    center_mask = COLUMN_MASKS[3]
    score += bin(position & center_mask).count('1') * 6
    score -= bin(opponent & center_mask).count('1') * 6

    return score


def _new_stats(num_moves, player):
    return {
        "player": player,
        "pieces": num_moves,
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


def _record_stats(stats, selected_move, action, start, deadline):
    global _LAST_SEARCH_STATS

    now = time.perf_counter()
    stats["action"] = action
    stats["selected_move"] = selected_move
    stats["elapsed_seconds"] = now - start
    stats["deadline_margin_seconds"] = deadline - now
    _LAST_SEARCH_STATS = dict(stats)


def main():
    empty_board = [[0 for _ in range(COLS)] for _ in range(ROWS)]
    print(make_move(empty_board, 1))


if __name__ == "__main__":
    main()
