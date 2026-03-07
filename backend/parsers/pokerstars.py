"""
PokerStars hand history parser.

Format reference: PokerStars .txt hand history files (No-Limit Hold'em).

Each file contains exactly one hand.
"""

import re
from datetime import datetime
from pathlib import Path

from domain.action import Action, ActionType
from domain.hand import Hand, GameType
from domain.player import Player, Position
from domain.street import Street, StreetName
from parsers.base import BaseParser, ParseError

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

_HEADER = re.compile(
    r"PokerStars Hand #(?P<hand_id>\d+): "
    r"Hold'em No Limit \((?P<currency>[^)]+)\) - "
    r"(?P<datetime>\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}) \w+"
)
_BLINDS = re.compile(
    r"\(\$(?P<sb>[\d.]+)/\$(?P<bb>[\d.]+) (?P<currency_code>\w+)\)"
)
_TABLE = re.compile(r"Table '(?P<name>[^']+)'")
_SEAT = re.compile(r"Seat (?P<seat>\d+): (?P<name>.+?) \(\$(?P<stack>[\d.]+) in chips\)")
_POST_SB = re.compile(r"(?P<name>.+?): posts small blind \$(?P<amount>[\d.]+)")
_POST_BB = re.compile(r"(?P<name>.+?): posts big blind \$(?P<amount>[\d.]+)")
_POST_ANTE = re.compile(r"(?P<name>.+?): posts the ante \$(?P<amount>[\d.]+)")
_UNCALLED = re.compile(r"Uncalled bet \(\$(?P<amount>[\d.]+)\) returned to (?P<name>.+)")
_FOLD = re.compile(r"(?P<name>.+?): folds")
_CHECK = re.compile(r"(?P<name>.+?): checks")
_CALL = re.compile(r"(?P<name>.+?): calls \$(?P<amount>[\d.]+)(?P<allin> and is all-in)?")
_BET = re.compile(r"(?P<name>.+?): bets \$(?P<amount>[\d.]+)(?P<allin> and is all-in)?")
_RAISE = re.compile(r"(?P<name>.+?): raises \$[\d.]+ to \$(?P<amount>[\d.]+)(?P<allin> and is all-in)?")
_DEALT = re.compile(r"Dealt to (?P<name>.+?) \[(?P<cards>[^\]]+)\]")
_SHOWS = re.compile(r"(?P<name>.+?): shows \[(?P<cards>[^\]]+)\]")
_MUCKS = re.compile(r"(?P<name>.+?): mucks hand")
_COLLECTED = re.compile(r"(?P<name>.+?) collected \$(?P<amount>[\d.]+) from pot")
_FLOP = re.compile(r"\*\*\* FLOP \*\*\* \[(?P<cards>[^\]]+)\]")
_TURN = re.compile(r"\*\*\* TURN \*\*\* \[[^\]]+\] \[(?P<card>[^\]]+)\]")
_RIVER = re.compile(r"\*\*\* RIVER \*\*\* \[[^\]]+\] \[(?P<card>[^\]]+)\]")
_TOTAL_POT = re.compile(r"Total pot \$(?P<pot>[\d.]+)(?: \| Rake \$(?P<rake>[\d.]+))?")
_SUMMARY_SEAT = re.compile(
    r"Seat \d+: (?P<name>.+?) "
    r"(?:\([^)]+\) )?"
    r"(?:showed \[(?P<cards>[^\]]+)\] and (?:won|lost)|"
    r"(?P<folded>folded)|(?P<collected>collected)|(?P<mucked>mucked))"
)
_SUMMARY_WINNER = re.compile(
    r"Seat \d+: (?P<name>.+?) (?:\([^)]+\) )?collected \(\$(?P<amount>[\d.]+)\)"
)
_SUMMARY_LOST = re.compile(
    r"Seat \d+: (?P<name>.+?) (?:\([^)]+\) )?showed \[[^\]]+\] and lost"
)


class PokerStarsParser(BaseParser):

    def parse_file(self, path: Path) -> list[Hand]:
        try:
            text = Path(path).read_text(encoding="utf-8")
        except OSError as e:
            raise ParseError(f"Cannot read file {path}: {e}") from e

        lines = text.splitlines()
        if not lines:
            raise ParseError(f"File is empty: {path}")

        return [self._parse(lines, path)]

    # ------------------------------------------------------------------
    # Top-level parse
    # ------------------------------------------------------------------

    def _parse(self, lines: list[str], path: Path) -> Hand:
        # --- Header line ---
        header_match = _HEADER.match(lines[0])
        if not header_match:
            raise ParseError(
                f"Unrecognized file format (header mismatch): {path}\n"
                f"First line: {lines[0]!r}"
            )

        hand_id = header_match.group("hand_id")
        played_at = datetime.strptime(header_match.group("datetime"), "%Y/%m/%d %H:%M:%S")

        blinds_match = _BLINDS.search(lines[0])
        if not blinds_match:
            raise ParseError(f"Cannot parse blinds from header: {lines[0]!r}")
        small_blind = float(blinds_match.group("sb"))
        big_blind = float(blinds_match.group("bb"))
        currency = blinds_match.group("currency_code")

        table_match = _TABLE.match(lines[1]) if len(lines) > 1 else None
        table_name = table_match.group("name") if table_match else "Unknown"

        # --- Split into sections ---
        sections = self._split_sections(lines)

        # --- Players ---
        players = self._parse_seats(sections.get("seats", []))
        player_map: dict[str, Player] = {p.name: p for p in players}

        # --- Streets ---
        streets: list[Street] = []
        hero_name: str | None = None

        # Preflop
        preflop_lines = sections.get("preflop", [])
        preflop_street, hero_name = self._parse_preflop(preflop_lines, player_map)
        streets.append(preflop_street)

        # Postflop streets
        for section_name, street_name in [
            ("flop", StreetName.FLOP),
            ("turn", StreetName.TURN),
            ("river", StreetName.RIVER),
        ]:
            if section_name in sections:
                streets.append(self._parse_postflop_street(
                    sections[section_name], street_name
                ))

        # --- Showdown hole cards ---
        for line in sections.get("showdown", []):
            m = _SHOWS.match(line)
            if m and m.group("name") in player_map:
                player_map[m.group("name")].hole_cards = m.group("cards").split()

        # --- Results from summary ---
        pot, rake = 0.0, 0.0
        for line in sections.get("summary", []):
            m = _TOTAL_POT.match(line)
            if m:
                pot = float(m.group("pot"))
                rake = float(m.group("rake") or 0)

        # Net won from "collected" lines throughout the hand
        all_lines = "\n".join(sections.get("preflop", [])
                              + sections.get("flop", [])
                              + sections.get("turn", [])
                              + sections.get("river", [])
                              + sections.get("showdown", []))
        self._apply_collected(all_lines, player_map, big_blind)

        # Deduct invested amounts (posted + called + raised) from net_won
        self._apply_invested(preflop_street, player_map)
        for street in streets[1:]:
            self._apply_invested(street, player_map)

        # Walk detection: everyone folded to BB (no voluntary action preflop)
        is_walk = self._detect_walk(preflop_street, player_map)

        # All-in equity (not present in standard HH text — left for future enrichment)
        return Hand(
            hand_id=hand_id,
            game_type=GameType.NLHE,
            small_blind=small_blind,
            big_blind=big_blind,
            table_name=table_name,
            played_at=played_at,
            players=players,
            streets=streets,
            hero_name=hero_name,
            pot=pot,
            rake=rake,
            currency=currency,
            is_walk=is_walk,
        )

    # ------------------------------------------------------------------
    # Section splitting
    # ------------------------------------------------------------------

    def _split_sections(self, lines: list[str]) -> dict[str, list[str]]:
        sections: dict[str, list[str]] = {
            "seats": [],
            "preflop": [],
        }
        current = "seats"

        for line in lines[2:]:  # skip hand header and table line
            if line.startswith("*** HOLE CARDS ***"):
                current = "preflop"
            elif line.startswith("*** FLOP ***"):
                current = "flop"
                sections.setdefault("flop", []).append(line)
            elif line.startswith("*** TURN ***"):
                current = "turn"
                sections.setdefault("turn", []).append(line)
            elif line.startswith("*** RIVER ***"):
                current = "river"
                sections.setdefault("river", []).append(line)
            elif line.startswith("*** SHOW DOWN ***"):
                current = "showdown"
                sections.setdefault("showdown", [])
            elif line.startswith("*** SUMMARY ***"):
                current = "summary"
                sections.setdefault("summary", [])
            elif current == "seats":
                # Blind posts appear before *** HOLE CARDS *** — route them to preflop
                if _SEAT.match(line):
                    sections["seats"].append(line)
                else:
                    sections.setdefault("preflop", []).append(line)
            else:
                sections.setdefault(current, []).append(line)

        return sections

    # ------------------------------------------------------------------
    # Seat / player parsing
    # ------------------------------------------------------------------

    def _parse_seats(self, lines: list[str]) -> list[Player]:
        players = []
        for line in lines:
            m = _SEAT.match(line)
            if m:
                players.append(Player(
                    name=m.group("name"),
                    seat=int(m.group("seat")),
                    stack=float(m.group("stack")),
                ))
        return players

    # ------------------------------------------------------------------
    # Preflop parsing
    # ------------------------------------------------------------------

    def _parse_preflop(
        self, lines: list[str], player_map: dict[str, Player]
    ) -> tuple[Street, str | None]:
        actions: list[Action] = []
        hero_name: str | None = None

        for line in lines:
            # Hole cards
            m = _DEALT.match(line)
            if m:
                hero_name = m.group("name")
                if hero_name in player_map:
                    player_map[hero_name].hole_cards = m.group("cards").split()
                continue

            action = self._parse_action_line(line)
            if action:
                actions.append(action)

        return Street(name=StreetName.PREFLOP, actions=actions), hero_name

    # ------------------------------------------------------------------
    # Postflop street parsing
    # ------------------------------------------------------------------

    def _parse_postflop_street(self, lines: list[str], name: StreetName) -> Street:
        cards: list[str] = []
        actions: list[Action] = []

        for line in lines:
            # Extract board cards from street header
            if name == StreetName.FLOP:
                m = _FLOP.match(line)
                if m:
                    cards = m.group("cards").split()
                    continue
            elif name == StreetName.TURN:
                m = _TURN.match(line)
                if m:
                    cards = [m.group("card")]
                    continue
            elif name == StreetName.RIVER:
                m = _RIVER.match(line)
                if m:
                    cards = [m.group("card")]
                    continue

            action = self._parse_action_line(line)
            if action:
                actions.append(action)

        return Street(name=name, actions=actions, cards=cards)

    # ------------------------------------------------------------------
    # Single action line parsing
    # ------------------------------------------------------------------

    def _parse_action_line(self, line: str) -> Action | None:
        m = _POST_SB.match(line)
        if m:
            return Action(m.group("name"), ActionType.POST_SB, float(m.group("amount")))

        m = _POST_BB.match(line)
        if m:
            return Action(m.group("name"), ActionType.POST_BB, float(m.group("amount")))

        m = _POST_ANTE.match(line)
        if m:
            return Action(m.group("name"), ActionType.POST_ANTE, float(m.group("amount")))

        m = _FOLD.match(line)
        if m:
            return Action(m.group("name"), ActionType.FOLD)

        m = _CHECK.match(line)
        if m:
            return Action(m.group("name"), ActionType.CHECK)

        m = _CALL.match(line)
        if m:
            return Action(
                m.group("name"), ActionType.CALL,
                float(m.group("amount")),
                is_all_in=bool(m.group("allin")),
            )

        m = _BET.match(line)
        if m:
            return Action(
                m.group("name"), ActionType.BET,
                float(m.group("amount")),
                is_all_in=bool(m.group("allin")),
            )

        m = _RAISE.match(line)
        if m:
            return Action(
                m.group("name"), ActionType.RAISE,
                float(m.group("amount")),
                is_all_in=bool(m.group("allin")),
            )

        m = _SHOWS.match(line)
        if m:
            return Action(m.group("name"), ActionType.SHOWS)

        m = _MUCKS.match(line)
        if m:
            return Action(m.group("name"), ActionType.MUCKS)

        return None

    # ------------------------------------------------------------------
    # Net won calculation
    # ------------------------------------------------------------------

    def _apply_collected(
        self, text: str, player_map: dict[str, Player], big_blind: float
    ) -> None:
        for m in _COLLECTED.finditer(text):
            name = m.group("name")
            if name in player_map:
                player_map[name].net_won += float(m.group("amount"))
        # Uncalled bets are returned to the raiser — credit them back
        for m in _UNCALLED.finditer(text):
            name = m.group("name")
            if name in player_map:
                player_map[name].net_won += float(m.group("amount"))

    def _apply_invested(self, street: Street, player_map: dict[str, Player]) -> None:
        """Compute each player's total chip investment on this street and deduct it.

        RAISE amounts are TOTAL invested on the street (raise-to), so a RAISE
        supersedes all prior investments.  Posts, calls, and bets are deltas.
        """
        invested: dict[str, float] = {}
        skip = {ActionType.WINS, ActionType.SHOWS, ActionType.MUCKS}
        for action in street.actions:
            if not action.amount or action.action_type in skip:
                continue
            if action.action_type == ActionType.RAISE:
                invested[action.player_name] = action.amount
            else:
                invested[action.player_name] = (
                    invested.get(action.player_name, 0.0) + action.amount
                )
        for name, amount in invested.items():
            if name in player_map:
                player_map[name].net_won -= amount

    # ------------------------------------------------------------------
    # Walk detection
    # ------------------------------------------------------------------

    def _detect_walk(
        self, preflop: Street, player_map: dict[str, Player]
    ) -> bool:
        """
        A walk occurs when everyone folds to the BB and the BB wins without
        a voluntary decision. Detected when the only preflop actions are
        blinds/antes and folds, with no calls or raises from non-blind players.
        """
        voluntary_types = {ActionType.CALL, ActionType.RAISE, ActionType.BET, ActionType.CHECK}
        blind_posters = {
            a.player_name
            for a in preflop.actions
            if a.action_type in (ActionType.POST_SB, ActionType.POST_BB, ActionType.POST_ANTE)
        }
        for action in preflop.actions:
            if action.action_type in voluntary_types:
                if action.action_type == ActionType.CHECK and action.player_name in blind_posters:
                    # BB checking their option is not a walk
                    pass
                return False
        return True
