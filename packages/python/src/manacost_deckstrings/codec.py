"""Dependency-free Hearthstone deckstring version 1 codec."""

from __future__ import annotations

import base64
from collections.abc import Mapping, Sequence
from typing import Any


VERSION = 1
SUPPORTED_FORMATS = (1, 2, 3, 4)
MAX_ITEMS_PER_GROUP = 1_000_000


class DeckstringError(ValueError):
	"""Raised when a deck definition or deckstring is invalid."""


class _Reader:
	def __init__(self, data: bytes):
		self.data = data
		self.offset = 0

	@property
	def at_end(self) -> bool:
		return self.offset >= len(self.data)

	def byte(self) -> int:
		if self.at_end:
			raise DeckstringError("Unexpected end of deckstring.")
		value = self.data[self.offset]
		self.offset += 1
		return value

	def varint(self) -> int:
		result = 0
		shift = 0
		while True:
			value = self.byte()
			result |= (value & 0x7F) << shift
			if not value & 0x80:
				return result
			shift += 7
			if shift > 56:
				raise DeckstringError("Varint is too large.")

	def positive_varint(self, name: str) -> int:
		value = self.varint()
		if value <= 0:
			raise DeckstringError(f"{name} must be positive.")
		return value

	def group_count(self) -> int:
		value = self.varint()
		if value > MAX_ITEMS_PER_GROUP:
			raise DeckstringError("Deckstring item group is too large.")
		return value


def _write_varint(output: bytearray, value: int) -> None:
	if value < 0:
		raise DeckstringError("Cannot encode a negative varint.")
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
		raise DeckstringError(f"{name} must be a positive integer.")
	return value


def _tuple(value: Any, length: int, name: str) -> list[int]:
	if (
		isinstance(value, (str, bytes, bytearray))
		or not isinstance(value, Sequence)
		or len(value) != length
	):
		raise DeckstringError(f"{name} must contain exactly {length} integers.")

	result: list[int] = []
	for index, item in enumerate(value):
		if index == 1:
			if type(item) is not int or item < 0:
				raise DeckstringError(f"{name} count must be a non-negative integer.")
			result.append(item)
		else:
			result.append(_positive_integer(item, f"{name} DBF ID"))
	return result


def _canonical_deck(deck: Mapping[str, Any]) -> dict[str, Any]:
	format_value = deck.get("format")
	if type(format_value) is not int or format_value not in SUPPORTED_FORMATS:
		raise DeckstringError(f"Unsupported format {format_value!r}.")

	heroes_value = deck.get("heroes")
	if (
		isinstance(heroes_value, (str, bytes, bytearray))
		or not isinstance(heroes_value, Sequence)
	):
		raise DeckstringError("Deck heroes must be a sequence.")
	heroes = sorted(_positive_integer(hero, "hero DBF ID") for hero in heroes_value)

	cards_value = deck.get("cards")
	if (
		isinstance(cards_value, (str, bytes, bytearray))
		or not isinstance(cards_value, Sequence)
	):
		raise DeckstringError("Deck cards must be a sequence.")
	cards = [_tuple(card, 2, "card") for card in cards_value]
	cards = sorted((card for card in cards if card[1] != 0), key=lambda card: card[0])

	sideboards_value = deck.get("sideboardCards", [])
	if (
		isinstance(sideboards_value, (str, bytes, bytearray))
		or not isinstance(sideboards_value, Sequence)
	):
		raise DeckstringError("Deck sideboardCards must be a sequence.")
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
		raise DeckstringError("Deckstring must be a non-empty string.")
	try:
		data = base64.b64decode(deckstring, validate=True)
	except (ValueError, TypeError) as error:
		raise DeckstringError("Deckstring is not valid Base64.") from error

	reader = _Reader(data)
	if reader.byte() != 0:
		raise DeckstringError("Invalid reserved byte.")
	version = reader.varint()
	if version != VERSION:
		raise DeckstringError(f"Unsupported deckstring version {version}.")
	format_value = reader.varint()
	if format_value not in SUPPORTED_FORMATS:
		raise DeckstringError(f"Unsupported format {format_value}.")

	heroes = [reader.positive_varint("hero DBF ID") for _ in range(reader.group_count())]
	heroes.sort()

	cards: list[list[int]] = []
	for group in (1, 2, 3):
		for _ in range(reader.group_count()):
			dbf_id = reader.positive_varint("card DBF ID")
			count = reader.positive_varint("card count") if group == 3 else group
			cards.append([dbf_id, count])
	cards.sort(key=lambda card: card[0])

	sideboard_cards: list[list[int]] = []
	has_sideboard = 0 if reader.at_end else reader.varint()
	if has_sideboard not in (0, 1):
		raise DeckstringError("Invalid sideboard marker.")
	if has_sideboard:
		for group in (1, 2, 3):
			for _ in range(reader.group_count()):
				dbf_id = reader.positive_varint("sideboard DBF ID")
				count = reader.positive_varint("sideboard count") if group == 3 else group
				owner = reader.positive_varint("sideboard owner DBF ID")
				sideboard_cards.append([dbf_id, count, owner])
		sideboard_cards.sort(key=lambda card: (card[2], card[0]))

	return {
		"format": format_value,
		"heroes": heroes,
		"cards": cards,
		"sideboardCards": sideboard_cards,
	}
