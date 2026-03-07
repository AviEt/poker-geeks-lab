from dataclasses import dataclass, field
from enum import Enum

from domain.action import Action


class StreetName(str, Enum):
    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"


@dataclass
class Street:
    name: StreetName
    actions: list[Action] = field(default_factory=list)
    cards: list[str] = field(default_factory=list)  # board cards dealt on this street
