"""Public type definitions for the deckstring package."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal, TypedDict

DeckstringErrorCode = Literal[
    "invalid_input",
    "invalid_base64",
    "unexpected_end",
    "invalid_reserved",
    "unsupported_version",
    "unsupported_format",
    "invalid_varint",
    "invalid_id",
    "invalid_count",
    "invalid_sideboard",
    "trailing_data",
    "limit_exceeded",
    "invalid_deck",
]

# JSON-compatible aliases. Each card is a two-item list and each sideboard card
# is a three-item list; the wire-compatible shape is documented in README.md.
DeckCard = list[int]
SideboardCard = list[int]


class Deck(TypedDict):
    """Canonical, JSON-compatible deck representation."""

    format: int
    heroes: list[int]
    cards: list[DeckCard]
    sideboardCards: list[SideboardCard]


class ValidationIssue(TypedDict):
    code: DeckstringErrorCode
    path: str
    message: str


class ValidationResult(TypedDict):
    valid: bool
    errors: list[ValidationIssue]


class _OptionalExportName(TypedDict, total=False):
    name: str


class ExportMetadata(_OptionalExportName):
    comments: list[str]


class ParsedExport(TypedDict):
    deck: Deck
    deckstring: str
    metadata: ExportMetadata


class _OptionalCardCost(TypedDict, total=False):
    cost: int


class CardInfo(_OptionalCardCost):
    name: str


CardResolver = Callable[[int], CardInfo | None]
