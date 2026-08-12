# Manacost Labs Hearthstone Deckstrings for Python

A dependency-free Python 3.10+ implementation of the shared deckstring contract
in this repository.

```bash
python -m pip install manacost-deckstrings
```

## Usage

```python
from manacost_deckstrings import canonicalize, decode, encode, validate

deck = decode("AAEBAQcBBAMBAgMAAA==")
result = validate(deck)
canonical_deck = canonicalize(deck)
deckstring = encode(deck)
```

Full Hearthstone clipboard exports are supported without card data or network
access:

```python
from manacost_deckstrings import format_export, parse_export

parsed = parse_export(export_text)
text = format_export(parsed["deck"], parsed["metadata"])
```

`format_export` also accepts an optional resolver callable. It receives a card
DBF ID and returns `{"name": "Card", "cost": 3}` or `None`.

## Errors

The returned dictionary follows the shared
[deck schema](https://github.com/Manacost-Labs/hearthstone-deckstrings/blob/main/spec/deck.schema.json).

Invalid input raises `DeckstringError`. Its `code` attribute follows the shared
[error contract](https://github.com/Manacost-Labs/hearthstone-deckstrings/blob/main/spec/README.md);
callers should not match the human-readable message.

The package is release-ready for PyPI. Published releases use semantic
versioning and support Python 3.10 through 3.14.
