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


@dataclass
class Player:
    name: str
    seat: int
    stack: float                         # stack at start of hand
    position: Position = Position.UNKNOWN
    hole_cards: list[str] = field(default_factory=list)
    net_won: float = 0.0                 # amount won/lost this hand (in chips)
