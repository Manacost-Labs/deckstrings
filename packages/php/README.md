# Manacost Labs Hearthstone Deckstrings for PHP

A dependency-free PHP 8.2–8.5 implementation of the shared deckstring contract in
this repository.

```bash
composer require manacost-labs/hearthstone-deckstrings
```

## Usage

```php
<?php

require __DIR__ . '/vendor/autoload.php';

use ManacostLabs\Deckstrings\Deckstrings;

$deck = Deckstrings::decode('AAEBAQcBBAMBAgMAAA==');
$validation = Deckstrings::validate($deck);
$canonicalDeck = Deckstrings::canonicalize($deck);
$deckstring = Deckstrings::encode($deck);
```

Full Hearthstone clipboard exports are supported without card data or network
access:

```php
$parsed = Deckstrings::parseExport($exportText);
$text = Deckstrings::formatExport($parsed['deck'], $parsed['metadata']);
```

`formatExport` also accepts an optional resolver callable. It receives a card
DBF ID and returns `['name' => 'Card', 'cost' => 3]` or `null`.

## Errors

The returned associative array follows the shared
[deck schema](https://github.com/Manacost-Labs/deckstrings/blob/main/spec/deck.schema.json).

Invalid input raises `DeckstringException`. Its `getErrorCode()` value follows
the shared
[error contract](https://github.com/Manacost-Labs/deckstrings/blob/main/spec/README.md);
callers should not match the human-readable message.

The package is release-ready for Packagist and follows semantic versioning.
