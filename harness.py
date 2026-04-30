import argparse
import random

from main import COLS, ROWS, _drop_piece, _has_won, _valid_moves, make_move


def random_move(board, player):
    del player
    return random.choice(_valid_moves(board))


def play_game(red_bot, yellow_bot):
    board = [[0 for _ in range(COLS)] for _ in range(ROWS)]
    bots = {1: red_bot, 2: yellow_bot}
    player = 1

    for _ in range(ROWS * COLS):
        valid_moves = _valid_moves(board)
        col = bots[player](board, player)

        if col not in valid_moves:
            return 3 - player

        board = _drop_piece(board, col, player)
        if _has_won(board, player):
            return player

        player = 3 - player

    return 0


def run_matches(games, seed):
    random.seed(seed)
    results = {"bot_wins": 0, "random_wins": 0, "draws": 0}

    for game in range(games):
        bot_player = 1 if game % 2 == 0 else 2
        winner = play_game(
            make_move if bot_player == 1 else random_move,
            make_move if bot_player == 2 else random_move,
        )

        if winner == bot_player:
            results["bot_wins"] += 1
        elif winner == 0:
            results["draws"] += 1
        else:
            results["random_wins"] += 1

    return results


def main():
    parser = argparse.ArgumentParser(description="Run local Connect Four bot matches.")
    parser.add_argument("--games", type=int, default=20)
    parser.add_argument("--seed", type=int, default=1)
    args = parser.parse_args()

    results = run_matches(args.games, args.seed)
    print(f"games: {args.games}")
    print(f"bot wins: {results['bot_wins']}")
    print(f"random wins: {results['random_wins']}")
    print(f"draws: {results['draws']}")


if __name__ == "__main__":
    main()
