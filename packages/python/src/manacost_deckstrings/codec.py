"""Dependency-free Hearthstone deckstring version 1 codec."""

from __future__ import annotations

import base64
from collections.abc import Mapping, Sequence
from typing import Any


VERSION = 1
SUPPORTED_FORMATS = (1, 2, 3, 4)
MAX_ITEMS_PER_GROUP = 10_000
MAX_BASE64_LENGTH = 1_398_104
MAX_VARINT = 2_147_483_647


class DeckstringError(ValueError):
	"""Raised when a deck definition or deckstring is invalid."""

	def __init__(self, code: str, message: str):
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
					raise DeckstringError("unexpected_end", "Unexpected end of deckstring.")
				raise DeckstringError(
					"invalid_varint",
					"Deckstring contains a truncated varint.",
				)
			value = self.byte()
			result |= (value & 0x7F) << shift
			if not value & 0x80:
				if result > MAX_VARINT:
					raise DeckstringError("invalid_varint", "Deckstring varint is too large.")
				return result
			shift += 7
		raise DeckstringError("invalid_varint", "Deckstring varint is too large.")

	def positive_varint(self, name: str, code: str = "invalid_id") -> int:
		value = self.varint()
		if value <= 0:
			raise DeckstringError(code, f"{name} must be positive.")
		return value

	def group_count(self) -> int:
		value = self.varint()
		if value > MAX_ITEMS_PER_GROUP:
			raise DeckstringError("limit_exceeded", "Deckstring item group is too large.")
		return value


def _write_varint(output: bytearray, value: int) -> None:
	if value < 0:
		raise DeckstringError("invalid_varint", "Cannot encode a negative varint.")
	while True:
		byte = value & 0x7F
		value >>= 7
		if value:
			output.append(byte | 0x80)
		else:
			output.append(byte)
			return


def _positive_integer(value: Any, name: str) -> int:
	if type(value) is not int or value <= 0:
		raise DeckstringError("invalid_id", f"{name} must be a positive integer.")
	return value


def _tuple(value: Any, length: int, name: str) -> list[int]:
	if (
		isinstance(value, (str, bytes, bytearray))
		or not isinstance(value, Sequence)
		or len(value) != length
	):
		raise DeckstringError(
			"invalid_deck",
			f"{name} must contain exactly {length} integers.",
		)

	result: list[int] = []
	for index, item in enumerate(value):
		if index == 1:
			if type(item) is not int or item < 0:
				raise DeckstringError(
					"invalid_count",
					f"{name} count must be a non-negative integer.",
				)
			result.append(item)
		else:
			result.append(_positive_integer(item, f"{name} DBF ID"))
	return result


def _canonical_deck(deck: Mapping[str, Any]) -> dict[str, Any]:
	format_value = deck.get("format")
	if type(format_value) is not int or format_value not in SUPPORTED_FORMATS:
		raise DeckstringError("unsupported_format", f"Unsupported format {format_value!r}.")

	heroes_value = deck.get("heroes")
	if (
		isinstance(heroes_value, (str, bytes, bytearray))
		or not isinstance(heroes_value, Sequence)
	):
		raise DeckstringError("invalid_deck", "Deck heroes must be a sequence.")
	heroes = sorted(_positive_integer(hero, "hero DBF ID") for hero in heroes_value)

	cards_value = deck.get("cards")
	if (
		isinstance(cards_value, (str, bytes, bytearray))
		or not isinstance(cards_value, Sequence)
	):
		raise DeckstringError("invalid_deck", "Deck cards must be a sequence.")
	cards = [_tuple(card, 2, "card") for card in cards_value]
	cards = sorted((card for card in cards if card[1] != 0), key=lambda card: card[0])

	sideboards_value = deck.get("sideboardCards", [])
	if (
		isinstance(sideboards_value, (str, bytes, bytearray))
		or not isinstance(sideboards_value, Sequence)
	):
		raise DeckstringError("invalid_deck", "Deck sideboardCards must be a sequence.")
	sideboards = [_tuple(card, 3, "sideboard card") for card in sideboards_value]
	sideboards = sorted(
		(card for card in sideboards if card[1] != 0),
		key=lambda card: (card[2], card[0]),
	)

	return {
		"format": format_value,
		"heroes": heroes,
		"cards": cards,
		"sideboardCards": sideboards,
	}


def _partition(cards: Sequence[Sequence[int]]) -> tuple[list[Any], list[Any], list[Any]]:
	groups: tuple[list[Any], list[Any], list[Any]] = ([], [], [])
	for card in cards:
		index = 0 if card[1] == 1 else 1 if card[1] == 2 else 2
		groups[index].append(card)
	return groups


def encode(deck: Mapping[str, Any]) -> str:
	"""Encode a deck definition into a canonical Hearthstone deckstring."""

	canonical = _canonical_deck(deck)
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


def decode(deckstring: str) -> dict[str, Any]:
	"""Decode a Hearthstone deckstring into a canonical deck definition."""

	if not isinstance(deckstring, str) or not deckstring:
		raise DeckstringError("invalid_input", "Deckstring must be a non-empty string.")
	if len(deckstring) > MAX_BASE64_LENGTH:
		raise DeckstringError(
			"limit_exceeded",
			"Deckstring exceeds the maximum supported size.",
		)
	try:
		data = base64.b64decode(deckstring, validate=True)
	except (ValueError, TypeError) as error:
		raise DeckstringError("invalid_base64", "Deckstring is not valid Base64.") from error

	reader = _Reader(data)
	if reader.byte() != 0:
		raise DeckstringError("invalid_reserved", "Invalid reserved byte.")
	version = reader.varint()
	if version != VERSION:
		raise DeckstringError(
			"unsupported_version",
			f"Unsupported deckstring version {version}.",
		)
	format_value = reader.varint()
	if format_value not in SUPPORTED_FORMATS:
		raise DeckstringError("unsupported_format", f"Unsupported format {format_value}.")

	hero_count = reader.group_count()
	if hero_count == 0:
		raise DeckstringError("invalid_count", "Deckstring must contain at least one hero.")
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

	return {
		"format": format_value,
		"heroes": heroes,
		"cards": cards,
		"sideboardCards": sideboard_cards,
	}
