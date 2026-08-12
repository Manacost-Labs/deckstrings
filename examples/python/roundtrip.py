"""Dependency-free consumer example for manacost-deckstrings."""

from manacost_deckstrings import (
    DeckstringError,
    canonicalize,
    decode,
    encode,
    format_export,
    parse_export,
    validate,
)

source = {
    "format": 1,
    "heroes": [7],
    "cards": [[4, 1], [1, 2]],
    "sideboardCards": [[5, 1, 90749]],
}

canonical = canonicalize(source)
assert canonical["cards"] == [[1, 2], [4, 1]]
assert validate(canonical)["valid"] is True

deckstring = encode(canonical)
assert decode(deckstring) == canonical

parsed = parse_export(f"### API example\n# Format: Wild\n#\n{deckstring}")
assert parsed["metadata"]["name"] == "API example"
assert parsed["deckstring"] == deckstring

cards = {
    1: {"name": "First Card", "cost": 1},
    4: {"name": "Fourth Card", "cost": 4},
    5: {"name": "Sideboard Card"},
}
formatted = format_export(
    parsed["deck"],
    {"name": "API example", "comments": ["Format: Wild"]},
    cards.get,
)
assert "# 2x (1) First Card" in formatted
assert "# 1x (0) Sideboard Card [sideboard:90749]" in formatted

try:
    decode("not-base64!")
except DeckstringError as error:
    assert error.code == "invalid_base64"
else:
    raise AssertionError("invalid input should raise DeckstringError")

print(formatted)
