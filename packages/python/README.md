# Manacost Labs Hearthstone Deckstrings for Python

A dependency-free Python 3.9+ implementation of the shared deckstring contract
in this repository.

```python
from manacost_deckstrings import decode, encode

deck = decode("AAEBAQcBBAMBAgMAAA==")
deckstring = encode(deck)
```

The returned dictionary follows `../../spec/deck.schema.json`.

Invalid input raises `DeckstringError`. Its `code` attribute follows the shared
error contract in `../../spec/README.md`; callers should not match the
human-readable message.

This package is under active development and has not been published to PyPI
yet.
