"""
Poker equity calculation using exact enumeration.

Enumerates all possible run-outs to produce deterministic, exact results.
"""

from itertools import combinations

from treys import Card, Evaluator

_EVALUATOR = Evaluator()
_RANKS = "23456789TJQKA"
_SUITS = "hdcs"
_ALL_CARDS = [r + s for r in _RANKS for s in _SUITS]


def calculate_equity(
    players: dict[str, list[str]],
    board: list[str] | None = None,
) -> dict[str, float]:
    """
    Calculate equity for each player via exact enumeration of all run-outs.

    Args:
        players: {player_name: [card1, card2]}
        board:   community cards already on the table (empty = preflop)

    Returns:
        {player_name: equity_fraction}  (values sum to exactly 1.0)
    """
    if board is None:
        board = []

    used: set[str] = set()
    for cards in players.values():
        used.update(cards)
    used.update(board)

    remaining = [c for c in _ALL_CARDS if c not in used]
    cards_needed = 5 - len(board)

    player_names = list(players.keys())
    treys_hands = {
        name: [Card.new(c) for c in cards]
        for name, cards in players.items()
    }
    treys_board_base = [Card.new(c) for c in board]

    wins: dict[str, float] = {name: 0.0 for name in player_names}
    total = 0

    for run in combinations(remaining, cards_needed):
        full_board = treys_board_base + [Card.new(c) for c in run]
        scores = {
            name: _EVALUATOR.evaluate(full_board, hand)
            for name, hand in treys_hands.items()
        }
        best = min(scores.values())
        winners = [n for n, s in scores.items() if s == best]
        share = 1.0 / len(winners)
        for w in winners:
            wins[w] += share
        total += 1

    return {name: wins[name] / total for name in player_names}
