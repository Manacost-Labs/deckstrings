# Manacost Labs Hearthstone Deckstrings for PHP

A dependency-free PHP 8.1+ implementation of the shared deckstring contract in
this repository.

```php
use ManacostLabs\Deckstrings\Deckstrings;

$deck = Deckstrings::decode('AAEBAQcBBAMBAgMAAA==');
$deckstring = Deckstrings::encode($deck);
```

The returned associative array follows `../../spec/deck.schema.json`.

Invalid input raises `DeckstringException`. Its `getErrorCode()` value follows
the shared error contract in `../../spec/README.md`; callers should not match
the human-readable message.

This package is under active development and has not been published to
Packagist yet.
