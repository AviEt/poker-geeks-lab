"""
Use case: parse a hand history file and persist all hands to the database.

Returns a summary dict:
    {"imported": N, "skipped": M, "errors": [...]}

"imported" = new hands written to DB
"skipped"  = hands already present (duplicate hand_id)
"errors"   = list of error strings for hands that failed to persist
"""

from pathlib import Path

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from db.repository import HandRepository
from parsers.base import ParseError
from parsers.ggpoker import GGPokerParser
from parsers.pokerstars import PokerStarsParser


def _detect_parser(path: Path):
    text = path.read_text(encoding="utf-8", errors="replace")
    if "Poker Hand #RC" in text:
        return GGPokerParser()
    return PokerStarsParser()


def import_hands(path: Path, *, engine: Engine) -> dict:
    """Parse *path* and persist all hands. Auto-detects format."""
    imported = 0
    skipped = 0
    errors: list[str] = []

    try:
        parser = _detect_parser(path)
        hands = parser.parse_file(path)
    except ParseError as exc:
        return {"imported": 0, "skipped": 0, "errors": [str(exc)]}

    with Session(engine) as session:
        repo = HandRepository(session)
        for hand in hands:
            try:
                result = repo.save_hand(hand)
                if result is None:
                    skipped += 1
                else:
                    imported += 1
            except Exception as exc:  # noqa: BLE001
                errors.append(f"Hand {hand.hand_id}: {exc}")

    return {"imported": imported, "skipped": skipped, "errors": errors}
