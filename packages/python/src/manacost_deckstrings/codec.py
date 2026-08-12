"""Dependency-free Hearthstone deckstring version 1 codec."""

from __future__ import annotations

import base64
from collections.abc import Mapping, Sequence
from typing import Final, cast

from .types import Deck, DeckstringErrorCode, ValidationIssue, ValidationResult

VERSION: Final = 1
SUPPORTED_FORMATS: Final = (1, 2, 3, 4)
MAX_ITEMS_PER_GROUP: Final = 10_000
MAX_ITEMS_PER_DECK: Final = 30_000
MAX_TOP_LEVEL_PROPERTIES: Final = 16
MAX_DECODED_LENGTH: Final = 1_048_576
MAX_BASE64_LENGTH: Final = 1_398_104
MAX_VARINT: Final = 2_147_483_647


class DeckstringError(ValueError):
    """Raised when a deck definition or deckstring is invalid."""

    def __init__(self, code: DeckstringErrorCode, message: str):
        super().__init__(message)
        self.code = code


class _Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.offset = 0

    @property
    def at_end(self) -> bool:
        return self.offset >= len(self.data)

    def byte(self) -> int:
        if self.at_end:
            raise DeckstringError("unexpected_end", "Unexpected end of deckstring.")
        value = self.data[self.offset]
        self.offset += 1
        return value

    def varint(self) -> int:
        result = 0
        shift = 0
        for byte_index in range(5):
            if self.at_end:
                if byte_index == 0:
                    raise DeckstringError(
                        "unexpected_end", "Unexpected end of deckstring."
                    )
                raise DeckstringError(
                    "invalid_varint", "Deckstring contains a truncated varint."
                )
            value = self.byte()
            result |= (value & 0x7F) << shift
            if not value & 0x80:
                if result > MAX_VARINT:
                    raise DeckstringError(
                        "invalid_varint", "Deckstring varint is too large."
                    )
                return result
            shift += 7
        raise DeckstringError("invalid_varint", "Deckstring varint is too large.")

    def positive_varint(
        self,
        name: str,
        code: DeckstringErrorCode = "invalid_id",
    ) -> int:
        value = self.varint()
        if value <= 0:
            raise DeckstringError(code, f"{name} must be positive.")
        return value

    def group_count(self) -> int:
        value = self.varint()
        if value > MAX_ITEMS_PER_GROUP:
            raise DeckstringError(
                "limit_exceeded", "Deckstring item group is too large."
            )
        return value


def _write_varint(output: bytearray, value: int) -> None:
    if value < 0 or value > MAX_VARINT:
        raise DeckstringError(
            "invalid_varint", "Cannot encode a varint outside the supported range."
        )
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            output.append(byte | 0x80)
        else:
            output.append(byte)
            return


def _is_sequence(value: object) -> bool:
    return not isinstance(value, (str, bytes, bytearray)) and isinstance(
        value, Sequence
    )


def _issue(
    code: DeckstringErrorCode,
    path: str,
    message: str,
) -> ValidationIssue:
    return {"code": code, "path": path, "message": message}


def _validate_deck(deck: object, *, allow_zero_counts: bool) -> list[ValidationIssue]:
    errors: list[ValidationIssue] = []
    if not isinstance(deck, Mapping):
        return [_issue("invalid_deck", "", "deck must be an object")]

    if len(deck) > MAX_TOP_LEVEL_PROPERTIES:
        return [_issue("limit_exceeded", "", "deck contains too many properties")]

    total_items = 0
    for group_name in ("heroes", "cards", "sideboardCards"):
        value = deck.get(group_name)
        if _is_sequence(value):
            total_items += len(cast(Sequence[object], value))
    if total_items > MAX_ITEMS_PER_DECK:
        return [_issue("limit_exceeded", "", "deck contains too many items")]

    for property_name in deck:
        if not isinstance(property_name, str) or property_name not in {
            "format",
            "heroes",
            "cards",
            "sideboardCards",
        }:
            errors.append(
                _issue(
                    "invalid_deck",
                    str(property_name),
                    "deck contains an unknown property",
                )
            )

    format_value = deck.get("format")
    if type(format_value) is not int or format_value not in SUPPORTED_FORMATS:
        errors.append(_issue("unsupported_format", "format", "format is not supported"))

    heroes_value = deck.get("heroes")
    if not _is_sequence(heroes_value):
        errors.append(_issue("invalid_deck", "heroes", "heroes must be an array"))
    else:
        heroes = cast(Sequence[object], heroes_value)
        if not heroes:
            errors.append(
                _issue("invalid_count", "heroes", "at least one hero is required")
            )
        if len(heroes) > MAX_ITEMS_PER_GROUP:
            errors.append(_issue("limit_exceeded", "heroes", "hero group is too large"))
        seen_heroes: set[int] = set()
        for index, hero in enumerate(heroes):
            path = f"heroes[{index}]"
            if type(hero) is not int or hero <= 0 or hero > MAX_VARINT:
                errors.append(
                    _issue("invalid_id", path, "hero DBF ID must be a positive integer")
                )
            elif hero in seen_heroes:
                errors.append(_issue("invalid_deck", path, "hero DBF ID is duplicated"))
            else:
                seen_heroes.add(hero)

    cards_value = deck.get("cards")
    if not _is_sequence(cards_value):
        errors.append(_issue("invalid_deck", "cards", "cards must be an array"))
    else:
        cards = cast(Sequence[object], cards_value)
        seen_cards: set[int] = set()
        group_counts = [0, 0, 0]
        for index, card_value in enumerate(cards):
            base_path = f"cards[{index}]"
            if (
                not _is_sequence(card_value)
                or len(cast(Sequence[object], card_value)) != 2
            ):
                errors.append(
                    _issue("invalid_deck", base_path, "card must contain two integers")
                )
                continue
            card = cast(Sequence[object], card_value)
            dbf_id, count = card
            valid_id = type(dbf_id) is int and 0 < dbf_id <= MAX_VARINT
            if not valid_id:
                errors.append(
                    _issue(
                        "invalid_id",
                        f"{base_path}[0]",
                        "card DBF ID must be a positive integer",
                    )
                )
            valid_count = type(count) is int and 0 <= count <= MAX_VARINT
            if not valid_count or (count == 0 and not allow_zero_counts):
                errors.append(
                    _issue(
                        "invalid_count",
                        f"{base_path}[1]",
                        "card count must be a positive integer",
                    )
                )
            if valid_count and count == 0 and allow_zero_counts:
                continue
            if valid_id:
                dbf_id_int = cast(int, dbf_id)
                if dbf_id_int in seen_cards:
                    errors.append(
                        _issue(
                            "invalid_deck",
                            f"{base_path}[0]",
                            "card DBF ID is duplicated",
                        )
                    )
                else:
                    seen_cards.add(dbf_id_int)
            if valid_count and cast(int, count) > 0:
                group = 0 if count == 1 else 1 if count == 2 else 2
                group_counts[group] += 1
        if any(count > MAX_ITEMS_PER_GROUP for count in group_counts):
            errors.append(_issue("limit_exceeded", "cards", "card group is too large"))

    sideboards_value = deck.get("sideboardCards", [])
    if not _is_sequence(sideboards_value):
        errors.append(
            _issue("invalid_deck", "sideboardCards", "sideboardCards must be an array")
        )
    else:
        sideboards = cast(Sequence[object], sideboards_value)
        seen_sideboards: set[tuple[int, int]] = set()
        group_counts = [0, 0, 0]
        for index, card_value in enumerate(sideboards):
            base_path = f"sideboardCards[{index}]"
            if (
                not _is_sequence(card_value)
                or len(cast(Sequence[object], card_value)) != 3
            ):
                errors.append(
                    _issue(
                        "invalid_deck",
                        base_path,
                        "sideboard card must contain three integers",
                    )
                )
                continue
            card = cast(Sequence[object], card_value)
            dbf_id, count, owner = card
            valid_id = type(dbf_id) is int and 0 < dbf_id <= MAX_VARINT
            valid_owner = type(owner) is int and 0 < owner <= MAX_VARINT
            if not valid_id:
                errors.append(
                    _issue(
                        "invalid_id",
                        f"{base_path}[0]",
                        "sideboard DBF ID must be a positive integer",
                    )
                )
            valid_count = type(count) is int and 0 <= count <= MAX_VARINT
            if not valid_count or (count == 0 and not allow_zero_counts):
                errors.append(
                    _issue(
                        "invalid_count",
                        f"{base_path}[1]",
                        "sideboard count must be a positive integer",
                    )
                )
            if not valid_owner:
                errors.append(
                    _issue(
                        "invalid_id",
                        f"{base_path}[2]",
                        "sideboard owner DBF ID must be a positive integer",
                    )
                )
            if valid_count and count == 0 and allow_zero_counts:
                continue
            if valid_id and valid_owner:
                sideboard_key = (cast(int, owner), cast(int, dbf_id))
                if sideboard_key in seen_sideboards:
                    errors.append(
                        _issue(
                            "invalid_deck",
                            base_path,
                            "sideboard owner and card pair is duplicated",
                        )
                    )
                else:
                    seen_sideboards.add(sideboard_key)
            if valid_count and cast(int, count) > 0:
                group = 0 if count == 1 else 1 if count == 2 else 2
                group_counts[group] += 1
        if any(count > MAX_ITEMS_PER_GROUP for count in group_counts):
            errors.append(
                _issue(
                    "limit_exceeded", "sideboardCards", "sideboard group is too large"
                )
            )

    return errors


def validate(deck: object) -> ValidationResult:
    """Return all validation issues without raising for ordinary invalid input."""

    errors = _validate_deck(deck, allow_zero_counts=False)
    return {"valid": not errors, "errors": errors}


def canonicalize(deck: Mapping[str, object]) -> Deck:
    """Return a new canonical deck without mutating caller-owned values."""

    errors = _validate_deck(deck, allow_zero_counts=True)
    if errors:
        first = errors[0]
        location = f" at {first['path']}" if first["path"] else ""
        raise DeckstringError(first["code"], f"{first['message']}{location}.")

    format_value = cast(int, deck["format"])
    heroes_value = cast(Sequence[int], deck["heroes"])
    cards_value = cast(Sequence[Sequence[int]], deck["cards"])
    sideboards_value = cast(Sequence[Sequence[int]], deck.get("sideboardCards", []))

    return {
        "format": format_value,
        "heroes": sorted(heroes_value),
        "cards": sorted(
            ([card[0], card[1]] for card in cards_value if card[1] != 0),
            key=lambda card: card[0],
        ),
        "sideboardCards": sorted(
            ([card[0], card[1], card[2]] for card in sideboards_value if card[1] != 0),
            key=lambda card: (card[2], card[0]),
        ),
    }


def _partition(cards: Sequence[Sequence[int]]) -> tuple[list[Sequence[int]], ...]:
    groups: tuple[list[Sequence[int]], ...] = ([], [], [])
    for card in cards:
        index = 0 if card[1] == 1 else 1 if card[1] == 2 else 2
        groups[index].append(card)
    return groups


def encode(deck: Mapping[str, object]) -> str:
    """Encode a deck definition into a canonical Hearthstone deckstring."""

    canonical = canonicalize(deck)
    output = bytearray((0,))
    _write_varint(output, VERSION)
    _write_varint(output, canonical["format"])
    _write_varint(output, len(canonical["heroes"]))
    for hero in canonical["heroes"]:
        _write_varint(output, hero)

    for group_index, group in enumerate(_partition(canonical["cards"])):
        _write_varint(output, len(group))
        for card in group:
            _write_varint(output, card[0])
            if group_index == 2:
                _write_varint(output, card[1])

    if not canonical["sideboardCards"]:
        _write_varint(output, 0)
        return base64.b64encode(output).decode("ascii")

    _write_varint(output, 1)
    for group_index, group in enumerate(_partition(canonical["sideboardCards"])):
        _write_varint(output, len(group))
        for card in group:
            _write_varint(output, card[0])
            if group_index == 2:
                _write_varint(output, card[1])
            _write_varint(output, card[2])

    return base64.b64encode(output).decode("ascii")


def decode(deckstring: str) -> Deck:
    """Decode a Hearthstone deckstring into a canonical deck definition."""

    if not isinstance(deckstring, str) or not deckstring:
        raise DeckstringError("invalid_input", "Deckstring must be a non-empty string.")
    if len(deckstring) > MAX_BASE64_LENGTH:
        raise DeckstringError(
            "limit_exceeded", "Deckstring exceeds the maximum supported size."
        )
    try:
        data = base64.b64decode(deckstring, validate=True)
    except (ValueError, TypeError) as error:
        raise DeckstringError(
            "invalid_base64", "Deckstring is not valid Base64."
        ) from error
    if len(data) > MAX_DECODED_LENGTH:
        raise DeckstringError(
            "limit_exceeded", "Deckstring exceeds the maximum supported size."
        )

    reader = _Reader(data)
    if reader.byte() != 0:
        raise DeckstringError("invalid_reserved", "Invalid reserved byte.")
    version = reader.varint()
    if version != VERSION:
        raise DeckstringError(
            "unsupported_version", f"Unsupported deckstring version {version}."
        )
    format_value = reader.varint()
    if format_value not in SUPPORTED_FORMATS:
        raise DeckstringError(
            "unsupported_format", f"Unsupported format {format_value}."
        )

    hero_count = reader.group_count()
    if hero_count == 0:
        raise DeckstringError(
            "invalid_count", "Deckstring must contain at least one hero."
        )
    heroes = [reader.positive_varint("hero DBF ID") for _ in range(hero_count)]
    heroes.sort()

    cards: list[list[int]] = []
    for group in (1, 2, 3):
        for _ in range(reader.group_count()):
            dbf_id = reader.positive_varint("card DBF ID")
            count = (
                reader.positive_varint("card count", "invalid_count")
                if group == 3
                else group
            )
            cards.append([dbf_id, count])
    cards.sort(key=lambda card: card[0])

    sideboard_cards: list[list[int]] = []
    has_sideboard = 0 if reader.at_end else reader.varint()
    if has_sideboard not in (0, 1):
        raise DeckstringError("invalid_sideboard", "Invalid sideboard marker.")
    if has_sideboard:
        for group in (1, 2, 3):
            for _ in range(reader.group_count()):
                dbf_id = reader.positive_varint("sideboard DBF ID")
                count = (
                    reader.positive_varint("sideboard count", "invalid_count")
                    if group == 3
                    else group
                )
                owner = reader.positive_varint("sideboard owner DBF ID")
                sideboard_cards.append([dbf_id, count, owner])
        sideboard_cards.sort(key=lambda card: (card[2], card[0]))
    if not reader.at_end:
        raise DeckstringError("trailing_data", "Deckstring contains trailing data.")

    return canonicalize(
        {
            "format": format_value,
            "heroes": heroes,
            "cards": cards,
            "sideboardCards": sideboard_cards,
        }
    )
