from dataclasses import dataclass, field
from enum import Enum


class Position(str, Enum):
    SB = "SB"
    BB = "BB"
    UTG = "UTG"
    UTG1 = "UTG+1"
    UTG2 = "UTG+2"
    MP = "MP"
    MP1 = "MP+1"
    HJ = "HJ"
    CO = "CO"
    BTN = "BTN"
    UNKNOWN = "UNKNOWN"


# Position templates indexed by player count.
# Ordered clockwise starting from the seat after the button (SB).
_POSITION_TABLE: dict[int, list[Position]] = {
    2: [Position.SB, Position.BB],
    3: [Position.SB, Position.BB, Position.BTN],
    4: [Position.SB, Position.BB, Position.CO, Position.BTN],
    5: [Position.SB, Position.BB, Position.UTG, Position.CO, Position.BTN],
    6: [Position.SB, Position.BB, Position.UTG, Position.HJ, Position.CO, Position.BTN],
    7: [Position.SB, Position.BB, Position.UTG, Position.MP, Position.HJ, Position.CO, Position.BTN],
    8: [Position.SB, Position.BB, Position.UTG, Position.UTG1, Position.MP, Position.HJ, Position.CO, Position.BTN],
    9: [Position.SB, Position.BB, Position.UTG, Position.UTG1, Position.UTG2, Position.MP, Position.HJ, Position.CO, Position.BTN],
    10: [Position.SB, Position.BB, Position.UTG, Position.UTG1, Position.UTG2, Position.MP, Position.MP1, Position.HJ, Position.CO, Position.BTN],
}


def assign_positions(players: list['Player'], button_seat: int) -> None:
    """Assign positions to players in-place based on button seat."""
    if len(players) < 2:
        return
    seats = sorted(p.seat for p in players)
    positions = _POSITION_TABLE.get(len(players))
    if not positions:
        return

    # Rotate seats so first seat is the one clockwise after the button.
    btn_idx = -1
    for i, s in enumerate(seats):
        if s == button_seat:
            btn_idx = i
            break
    if btn_idx == -1:
        return
    ordered = seats[btn_idx + 1:] + seats[:btn_idx + 1]

    seat_to_pos = dict(zip(ordered, positions))
    for player in players:
        player.position = seat_to_pos.get(player.seat, Position.UNKNOWN)


@dataclass
class Player:
    name: str
    seat: int
    stack: float                         # stack at start of hand
    position: Position = Position.UNKNOWN
    hole_cards: list[str] = field(default_factory=list)
    net_won: float = 0.0                 # amount won/lost this hand (in chips)
    pot_won_after_rake: float = 0.0      # sum of "collected" lines; pot hero won after rake deduction
