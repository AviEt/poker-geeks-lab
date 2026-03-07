from dataclasses import dataclass
from enum import Enum


class ActionType(str, Enum):
    POST_SB = "post_sb"
    POST_BB = "post_bb"
    POST_ANTE = "post_ante"
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    BET = "bet"
    RAISE = "raise"
    ALL_IN = "all_in"
    SHOWS = "shows"
    MUCKS = "mucks"
    WINS = "wins"


@dataclass
class Action:
    player_name: str
    action_type: ActionType
    amount: float | None = None  # amount put in (call/bet/raise total, not delta)
    is_all_in: bool = False
