from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from domain.player import Player
from domain.street import Street


class GameType(str, Enum):
    NLHE = "NLHoldem"      # No-Limit Hold'em
    PLO = "PLOmaha"        # Pot-Limit Omaha
    PLO5 = "PLO5"          # 5-card PLO


@dataclass
class Hand:
    hand_id: str                             # unique identifier from the hand history
    game_type: GameType
    small_blind: float
    big_blind: float
    table_name: str
    played_at: datetime
    players: list[Player] = field(default_factory=list)
    streets: list[Street] = field(default_factory=list)
    board: list[str] = field(default_factory=list)  # full board cards
    hero_name: str | None = None            # name of the player whose HH this is
    pot: float = 0.0                        # total pot at showdown
    rake: float = 0.0
    currency: str = "USD"
    is_walk: bool = False                   # everyone folded to BB; excluded from VPIP/PFR denominator
    cash_drop: float = 0.0                  # GGPoker promotional cash added to pot (not invested by any player)
    cashout_risk: float = 0.0               # GGPoker EV Cashout fee paid by player (extra rake-like deduction)
    # All-in equity fields (set when players are all-in with cards remaining)
    all_in_equity: dict[str, float] | None = None   # player_name → equity fraction (0.0–1.0)
    all_in_pot_bb: float | None = None              # total pot in big blinds at time of all-in
