import argparse
import random
import time
from dataclasses import dataclass, field

from bitboard_bot import make_move as bitboard_make_move
from bitboard_bot import get_last_search_stats as bitboard_get_last_search_stats
from main import (
    COLS,
    ROWS,
    _drop_piece,
    _has_won,
    _ordered_moves,
    _safe_moves,
    _valid_moves,
    get_last_search_stats,
    make_move,
)


@dataclass
class GameResult:
    winner: int
    reason: str
    final_board: list[list[int]]
    moves: list[tuple[int, int]] = field(default_factory=list)
    move_times: dict[int, list[float]] = field(default_factory=lambda: {1: [], 2: []})
    search_stats: dict[int, list[dict]] = field(default_factory=lambda: {1: [], 2: []})


def random_move(board, player):
    del player
    return random.choice(_valid_moves(board))


def center_move(board, player):
    del player
    return _ordered_moves(_valid_moves(board))[0]


def tactical_move(board, player):
    valid_moves = _valid_moves(board)
    opponent = 3 - player

    for col in _ordered_moves(valid_moves):
        if _has_won(_drop_piece(board, col, player), player):
            return col

    for col in _ordered_moves(valid_moves):
        if _has_won(_drop_piece(board, col, opponent), opponent):
            return col

    safe_moves = _safe_moves(board, valid_moves, player)
    return _ordered_moves(safe_moves or valid_moves)[0]


BOTS = {
    "bitboard": bitboard_make_move,
    "bot": make_move,
    "tactical": tactical_move,
    "center": center_move,
    "random": random_move,
}


def play_game(bots_by_player, time_limit_seconds=1.0):
    board = [[0 for _ in range(COLS)] for _ in range(ROWS)]
    result = GameResult(winner=0, reason="draw", final_board=board)
    player = 1

    for _ in range(ROWS * COLS):
        valid_moves = _valid_moves(board)
        bot_board = [row[:] for row in board]

        start = time.perf_counter()
        try:
            bot = bots_by_player[player]
            col = bot(bot_board, player)
        except Exception as exc:
            elapsed = time.perf_counter() - start
            result.move_times[player].append(elapsed)
            result.search_stats[player].append({})
            result.winner = 3 - player
            result.reason = f"player {player} crash: {type(exc).__name__}"
            result.final_board = board
            return result

        elapsed = time.perf_counter() - start
        result.move_times[player].append(elapsed)
        if bot is make_move:
            search_stats = get_last_search_stats()
        elif bot is bitboard_make_move:
            search_stats = bitboard_get_last_search_stats()
        else:
            search_stats = {}
        result.search_stats[player].append(search_stats)

        if elapsed > time_limit_seconds:
            result.winner = 3 - player
            result.reason = f"player {player} timeout"
            result.final_board = board
            return result

        if col not in valid_moves:
            result.winner = 3 - player
            result.reason = f"player {player} illegal move"
            result.final_board = board
            return result

        board = _drop_piece(board, col, player)
        result.moves.append((player, col))

        if _has_won(board, player):
            result.winner = player
            result.reason = "connect four"
            result.final_board = board
            return result

        player = 3 - player

    result.final_board = board
    return result


def run_matches(bot_a_name, bot_b_name, games, seed, time_limit_seconds, alternate_colors):
    random.seed(seed)
    stats = {
        "a_wins": 0,
        "b_wins": 0,
        "draws": 0,
        "timeouts": 0,
        "illegal_moves": 0,
        "crashes": 0,
        "a_time_total": 0.0,
        "b_time_total": 0.0,
        "a_time_count": 0,
        "b_time_count": 0,
        "a_time_max": 0.0,
        "b_time_max": 0.0,
        "a_search_count": 0,
        "b_search_count": 0,
        "a_depth_total": 0,
        "b_depth_total": 0,
        "a_depth_max": 0,
        "b_depth_max": 0,
        "a_nodes_total": 0,
        "b_nodes_total": 0,
        "a_nodes_max": 0,
        "b_nodes_max": 0,
        "a_cache_hits": 0,
        "b_cache_hits": 0,
        "a_cache_stores": 0,
        "b_cache_stores": 0,
        "a_search_timeouts": 0,
        "b_search_timeouts": 0,
        "a_margin_min": None,
        "b_margin_min": None,
        "a_actions": {},
        "b_actions": {},
        "results": [],
    }

    for game_index in range(games):
        a_player = 2 if alternate_colors and game_index % 2 else 1
        b_player = 3 - a_player
        labels_by_player = {a_player: "a", b_player: "b"}
        bots_by_player = {
            a_player: BOTS[bot_a_name],
            b_player: BOTS[bot_b_name],
        }

        result = play_game(bots_by_player, time_limit_seconds)
        stats["results"].append((result, labels_by_player))

        if result.winner == 0:
            stats["draws"] += 1
        else:
            stats[f"{labels_by_player[result.winner]}_wins"] += 1

        if "timeout" in result.reason:
            stats["timeouts"] += 1
        if "illegal move" in result.reason:
            stats["illegal_moves"] += 1
        if "crash" in result.reason:
            stats["crashes"] += 1

        for player, times in result.move_times.items():
            label = labels_by_player[player]
            stats[f"{label}_time_total"] += sum(times)
            stats[f"{label}_time_count"] += len(times)
            if times:
                stats[f"{label}_time_max"] = max(stats[f"{label}_time_max"], max(times))

        for player, metrics_by_move in result.search_stats.items():
            label = labels_by_player[player]
            for metrics in metrics_by_move:
                if metrics:
                    _add_search_metrics(stats, label, metrics)

    return stats


def _add_search_metrics(stats, label, metrics):
    stats[f"{label}_search_count"] += 1
    stats[f"{label}_depth_total"] += metrics.get("depth_reached", 0)
    stats[f"{label}_depth_max"] = max(stats[f"{label}_depth_max"], metrics.get("depth_reached", 0))
    stats[f"{label}_nodes_total"] += metrics.get("nodes", 0)
    stats[f"{label}_nodes_max"] = max(stats[f"{label}_nodes_max"], metrics.get("nodes", 0))
    stats[f"{label}_cache_hits"] += metrics.get("cache_hits", 0)
    stats[f"{label}_cache_stores"] += metrics.get("cache_stores", 0)

    if metrics.get("timed_out"):
        stats[f"{label}_search_timeouts"] += 1

    margin = metrics.get("deadline_margin_seconds")
    if margin is not None:
        current_min = stats[f"{label}_margin_min"]
        stats[f"{label}_margin_min"] = margin if current_min is None else min(current_min, margin)

    action = metrics.get("action", "unknown")
    actions = stats[f"{label}_actions"]
    actions[action] = actions.get(action, 0) + 1


def format_board(board):
    symbols = {0: ".", 1: "R", 2: "Y"}
    return "\n".join(" ".join(symbols[cell] for cell in row) for row in board)


def average_time(stats, label):
    count = stats[f"{label}_time_count"]
    if count == 0:
        return 0.0
    return stats[f"{label}_time_total"] / count


def average_search_depth(stats, label):
    count = stats[f"{label}_search_count"]
    if count == 0:
        return 0.0
    return stats[f"{label}_depth_total"] / count


def average_nodes(stats, label):
    count = stats[f"{label}_search_count"]
    if count == 0:
        return 0.0
    return stats[f"{label}_nodes_total"] / count


def cache_hit_rate(stats, label):
    hits = stats[f"{label}_cache_hits"]
    stores = stats[f"{label}_cache_stores"]
    total = hits + stores
    if total == 0:
        return 0.0
    return hits / total


def format_actions(actions):
    if not actions:
        return "n/a"
    return ", ".join(f"{name}:{count}" for name, count in sorted(actions.items()))


def print_search_summary(stats, label, name):
    count = stats[f"{label}_search_count"]
    if count == 0:
        print(f"bot {label.upper()} ({name}) search: n/a")
        return

    margin = stats[f"{label}_margin_min"]
    margin_text = "n/a" if margin is None else f"{margin:.4f}s"
    print(
        f"bot {label.upper()} ({name}) search: "
        f"depth avg/max {average_search_depth(stats, label):.2f}/{stats[f'{label}_depth_max']}, "
        f"nodes avg/max {average_nodes(stats, label):.0f}/{stats[f'{label}_nodes_max']}, "
        f"cache hit rate {cache_hit_rate(stats, label):.1%}, "
        f"internal timeouts {stats[f'{label}_search_timeouts']}, "
        f"min margin {margin_text}"
    )
    print(f"bot {label.upper()} actions: {format_actions(stats[f'{label}_actions'])}")


def print_summary(args, stats):
    print(f"games: {args.games}")
    print(f"bot A ({args.bot_a}) wins: {stats['a_wins']}")
    print(f"bot B ({args.bot_b}) wins: {stats['b_wins']}")
    print(f"draws: {stats['draws']}")
    print(f"timeouts: {stats['timeouts']}")
    print(f"illegal moves: {stats['illegal_moves']}")
    print(f"crashes: {stats['crashes']}")
    print(f"bot A avg/max move: {average_time(stats, 'a'):.4f}s / {stats['a_time_max']:.4f}s")
    print(f"bot B avg/max move: {average_time(stats, 'b'):.4f}s / {stats['b_time_max']:.4f}s")
    print_search_summary(stats, "a", args.bot_a)
    print_search_summary(stats, "b", args.bot_b)

    if args.show_games:
        for game_index, (result, labels_by_player) in enumerate(stats["results"], start=1):
            winner = "draw" if result.winner == 0 else f"bot {labels_by_player[result.winner].upper()}"
            moves = " ".join(str(col) for _, col in result.moves)
            print()
            print(f"game {game_index}: {winner}, {result.reason}")
            print(f"moves: {moves}")
            print(format_board(result.final_board))


def main():
    parser = argparse.ArgumentParser(description="Run local Connect Four bot simulations.")
    parser.add_argument("--bot-a", choices=sorted(BOTS), default="bot")
    parser.add_argument("--bot-b", choices=sorted(BOTS), default="random")
    parser.add_argument("--games", type=int, default=20)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--time-limit", type=float, default=1.0)
    parser.add_argument("--fixed-colors", action="store_true")
    parser.add_argument("--show-games", action="store_true")
    args = parser.parse_args()

    stats = run_matches(
        args.bot_a,
        args.bot_b,
        args.games,
        args.seed,
        args.time_limit,
        alternate_colors=not args.fixed_colors,
    )
    print_summary(args, stats)


if __name__ == "__main__":
    main()
