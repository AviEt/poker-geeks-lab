"""
GGPoker hand history parser.

Format notes vs PokerStars:
  - Header:     "Poker Hand #RC{id}:" instead of "PokerStars Hand #{id}:"
  - Showdown:   "*** SHOWDOWN ***" (no space) instead of "*** SHOW DOWN ***"
  - Shows:      appear in action sections (before SHOWDOWN marker), not after
  - Dealt to:   opponents listed without cards ("Dealt to name " with no brackets)
  - Multi-hand: one file contains many hands separated by blank lines
  - Rake line:  extra fields "Jackpot $X | Bingo $X | Fortune $X | Tax $X"
"""

import re
from datetime import datetime
from pathlib import Path

from domain.action import Action, ActionType
from domain.hand import Hand, GameType
from domain.player import Player, assign_positions
from domain.street import Street, StreetName
from parsers.base import BaseParser, ParseError

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

_HEADER = re.compile(
    r"Poker Hand #RC(?P<hand_id>\d+): "
    r"Hold'em No Limit \(\$(?P<sb>[\d.]+)/\$(?P<bb>[\d.]+)\) - "
    r"(?P<datetime>\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2})"
)
_TABLE = re.compile(r"Table '(?P<name>[^']+)'.*Seat #(?P<btn>\d+) is the button")
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
_TOTAL_POT = re.compile(r"Total pot \$(?P<pot>[\d.]+)")
_FEE_FIELD = re.compile(r"\| (?:Rake|Jackpot|Bingo|Fortune|Tax) \$(?P<amount>[\d.]+)")
_CASH_DROP = re.compile(r"Cash Drop to Pot : total \$(?P<amount>[\d.]+)")
# GGPoker hand boundary: starts a new hand block
_HAND_START = re.compile(r"^Poker Hand #RC\d+:")


class GGPokerParser(BaseParser):

    def parse_file(self, path: Path) -> list[Hand]:
        try:
            text = Path(path).read_text(encoding="utf-8")
        except OSError as e:
            raise ParseError(f"Cannot read file {path}: {e}") from e

        blocks = self._split_into_blocks(text)
        if not blocks:
            raise ParseError(f"No hands found in file: {path}")

        return [self._parse_block(block, path) for block in blocks]

    # ------------------------------------------------------------------
    # Split file into per-hand blocks
    # ------------------------------------------------------------------

    def _split_into_blocks(self, text: str) -> list[list[str]]:
        """Split file text into one list-of-lines per hand."""
        blocks: list[list[str]] = []
        current: list[str] = []

        for line in text.splitlines():
            if _HAND_START.match(line):
                if current:
                    blocks.append(current)
                current = [line]
            else:
                current.append(line)

        if current:
            blocks.append(current)

        return blocks

    # ------------------------------------------------------------------
    # Parse a single hand block
    # ------------------------------------------------------------------

    def _parse_block(self, lines: list[str], path: Path) -> Hand:
        header_match = _HEADER.match(lines[0])
        if not header_match:
            raise ParseError(
                f"Unrecognized GGPoker hand header: {lines[0]!r} in {path}"
            )

        hand_id = header_match.group("hand_id")
        small_blind = float(header_match.group("sb"))
        big_blind = float(header_match.group("bb"))
        played_at = datetime.strptime(header_match.group("datetime"), "%Y/%m/%d %H:%M:%S")

        table_match = _TABLE.match(lines[1]) if len(lines) > 1 else None
        table_name = table_match.group("name") if table_match else "Unknown"
        button_seat = int(table_match.group("btn")) if table_match else None

        sections = self._split_sections(lines)

        # GGPoker promotional cash drop (added to pot, not invested by any player)
        cash_drop = 0.0
        for line in sections.get("preflop", []):
            m = _CASH_DROP.match(line)
            if m:
                cash_drop = float(m.group("amount"))
                break

        players = self._parse_seats(sections.get("seats", []))
        if button_seat is not None:
            assign_positions(players, button_seat)
        player_map: dict[str, Player] = {p.name: p for p in players}

        streets: list[Street] = []
        hero_name: str | None = None

        preflop_lines = sections.get("preflop", [])
        preflop_street, hero_name = self._parse_preflop(preflop_lines, player_map)
        streets.append(preflop_street)

        for section_name, street_name in [
            ("flop", StreetName.FLOP),
            ("turn", StreetName.TURN),
            ("river", StreetName.RIVER),
        ]:
            if section_name in sections:
                streets.append(self._parse_postflop_street(
                    sections[section_name], street_name, player_map
                ))

        # Results — rake includes all GGPoker fee fields (Rake + Jackpot + Bingo + Fortune + Tax)
        pot, rake = 0.0, 0.0
        for line in sections.get("summary", []):
            m = _TOTAL_POT.match(line)
            if m:
                pot = float(m.group("pot"))
                rake = sum(float(fm.group("amount")) for fm in _FEE_FIELD.finditer(line))

        all_lines = "\n".join(
            sections.get("preflop", [])
            + sections.get("flop", [])
            + sections.get("turn", [])
            + sections.get("river", [])
            + sections.get("showdown", [])
        )
        self._apply_collected(all_lines, player_map)
        for street in streets:
            self._apply_invested(street, player_map)

        is_walk = self._detect_walk(preflop_street, player_map)

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
            currency="USD",
            is_walk=is_walk,
            cash_drop=cash_drop,
        )

    # ------------------------------------------------------------------
    # Section splitting (GGPoker uses *** SHOWDOWN *** without space)
    # ------------------------------------------------------------------

    def _split_sections(self, lines: list[str]) -> dict[str, list[str]]:
        sections: dict[str, list[str]] = {"seats": [], "preflop": []}
        current = "seats"

        for line in lines[2:]:
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
            elif line.startswith("*** SHOWDOWN ***"):
                current = "showdown"
                sections.setdefault("showdown", [])
            elif line.startswith("*** SUMMARY ***"):
                current = "summary"
                sections.setdefault("summary", [])
            elif current == "seats":
                if _SEAT.match(line):
                    sections["seats"].append(line)
                else:
                    sections["preflop"].append(line)
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
            # GGPoker: "Dealt to Hero [As Kh]" for hero, "Dealt to name " for others
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

    def _parse_postflop_street(
        self,
        lines: list[str],
        name: StreetName,
        player_map: dict[str, Player],
    ) -> Street:
        cards: list[str] = []
        actions: list[Action] = []

        for line in lines:
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

            # GGPoker: shows appear in action sections (before SHOWDOWN marker)
            shows_m = _SHOWS.match(line)
            if shows_m:
                name_shown = shows_m.group("name")
                if name_shown in player_map:
                    player_map[name_shown].hole_cards = shows_m.group("cards").split()
                continue

            action = self._parse_action_line(line)
            if action:
                actions.append(action)

        return Street(name=name, actions=actions, cards=cards)

    # ------------------------------------------------------------------
    # Action line parsing
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
    # Net won
    # ------------------------------------------------------------------

    def _apply_collected(self, text: str, player_map: dict[str, Player]) -> None:
        for m in _COLLECTED.finditer(text):
            name = m.group("name")
            if name in player_map:
                amount = float(m.group("amount"))
                player_map[name].net_won += amount
                player_map[name].pot_won_after_rake += amount
        # Uncalled bets are returned to the raiser — credit net_won but not pot_won_after_rake
        for m in _UNCALLED.finditer(text):
            name = m.group("name")
            if name in player_map:
                player_map[name].net_won += float(m.group("amount"))

    def _apply_invested(self, street: Street, player_map: dict[str, Player]) -> None:
        """Compute each player's total chip investment on this street and deduct it.

        RAISE amounts in PokerStars/GGPoker format are TOTAL invested on the street
        (e.g. "raises $0.50 to $0.62" → $0.62 total), so a RAISE supersedes all
        prior investments on the same street.  Posts, calls, and bets are deltas.
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
        blind_posters = {
            a.player_name
            for a in preflop.actions
            if a.action_type in (ActionType.POST_SB, ActionType.POST_BB, ActionType.POST_ANTE)
        }
        voluntary = {ActionType.CALL, ActionType.RAISE, ActionType.BET, ActionType.CHECK}
        for action in preflop.actions:
            if action.action_type in voluntary:
                if action.action_type == ActionType.CHECK and action.player_name in blind_posters:
                    pass
                else:
                    return False
        return True

