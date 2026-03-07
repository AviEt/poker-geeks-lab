from abc import ABC, abstractmethod
from pathlib import Path

from domain.hand import Hand


class ParseError(Exception):
    """Raised when a hand history file cannot be parsed."""


class BaseParser(ABC):
    @abstractmethod
    def parse_file(self, path: Path) -> list[Hand]:
        """Parse a hand history file and return all Hand objects found in it.

        PokerStars files contain one hand; GGPoker files contain many.
        Always returns a list so callers are format-agnostic.
        """
