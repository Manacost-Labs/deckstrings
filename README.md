# Manacost Labs Hearthstone Deckstrings

[![CI](https://github.com/Manacost-Labs/hearthstone-deckstrings/actions/workflows/ci.yml/badge.svg)](https://github.com/Manacost-Labs/hearthstone-deckstrings/actions/workflows/ci.yml)
[![License: ISC](https://img.shields.io/badge/license-ISC-blue.svg)](LICENSE)
[![Status: alpha](https://img.shields.io/badge/status-alpha-orange.svg)](ROADMAP.md)

A small, deterministic Hearthstone deckstring codec for backend applications.
The same version 1 wire format is implemented natively for JavaScript,
TypeScript, PHP, Python, and C#.

> **Alpha:** the JavaScript package preserves the upstream API, while the PHP,
> Python, and .NET packages are under active development and are not published
> to public registries yet.

## Why this fork

The original [HearthSim project](https://github.com/HearthSim/hearthstone-deckstrings)
provides the JavaScript codec. This fork keeps that compatibility and adds:

- native, dependency-free backend implementations;
- one shared JSON contract and fixture suite;
- byte-for-byte canonical encoding across languages;
- Wild, Standard, Classic, Twist, and sideboard support;
- stable machine-readable errors for malformed input;
- defensive limits for untrusted deckstrings.

The codec intentionally does not download card data or validate deck legality.
Names, images, rotations, and card metadata belong to a separate provider such
as [HearthstoneJSON](https://hearthstonejson.com/).

## Packages

| Ecosystem | Package | Runtime | Status |
| --- | --- | --- | --- |
| npm | `@manacost-labs/deckstrings` (planned) | Node.js / browser | alpha |
| Composer | `manacost-labs/hearthstone-deckstrings` | PHP 8.1+ | alpha |
| PyPI | `manacost-deckstrings` | Python 3.9+ | alpha |
| NuGet | `ManacostLabs.Deckstrings` | `netstandard2.0`, `net8.0` | alpha |

Until the first public release, install the repository from source. Registry
commands will be added only after the package names and release workflow have
been approved.

## Shared data model

Every implementation returns the same canonical representation:

```json
{
  "format": 1,
  "heroes": [7],
  "cards": [[1, 2], [2, 2], [3, 2], [4, 1]],
  "sideboardCards": [[5, 1, 90749]]
}
```

- `cards`: `[dbfId, count]`;
- `sideboardCards`: `[dbfId, count, ownerDbfId]`;
- heroes and cards are sorted by DBF ID;
- sideboard cards are sorted by owner and then DBF ID.

The normative definition is [spec/deck.schema.json](spec/deck.schema.json).

## JavaScript / TypeScript

```javascript
import { decode, encode, FormatType } from "deckstrings";

const deck = {
	cards: [[1, 2], [2, 2], [3, 2], [4, 1]], // [dbfId, count] pairs
	sideboardCards: [[5, 1, 90749]], // [dbfId, count, sideboardOwnerDbfId] triplets
	heroes: [7], // Garrosh Hellscream
	format: FormatType.FT_WILD, // or FT_STANDARD or FT_CLASSIC
};

const deckstring = encode(deck);
console.log(deckstring); // AAEBAQcBBAMBAgMAAQEF/cQFAAA=

const decoded = decode(deckstring);
console.log(JSON.stringify(deck) === JSON.stringify(decoded)); // true
```

## PHP

```php
use ManacostLabs\Deckstrings\Deckstrings;

$deck = Deckstrings::decode('AAEBAQcBBAMBAgMAAA==');
$deckstring = Deckstrings::encode($deck);
```

## Python

```python
from manacost_deckstrings import decode, encode

deck = decode("AAEBAQcBBAMBAgMAAA==")
deckstring = encode(deck)
```

## C# / .NET

```csharp
using ManacostLabs.Deckstrings;

var deck = Deckstrings.Decode("AAEBAQcBBAMBAgMAAA==");
var deckstring = Deckstrings.Encode(deck);
```

## Error handling

Invalid input raises an idiomatic exception with a stable code. Messages are
human-readable and may improve between releases; code values are the contract.

```javascript
import { decode, DeckstringError } from "deckstrings";

try {
	decode("not-base64!");
} catch (error) {
	if (error instanceof DeckstringError) {
		console.error(error.code); // invalid_base64
	}
}
```

See [the compatibility contract](spec/README.md#stable-error-contract) for all
codes and limits.

## Repository layout

```text
src/                 JavaScript/TypeScript reference implementation
packages/php/        Native PHP implementation
packages/python/     Native Python implementation
packages/dotnet/     Native C# implementation
fixtures/            Shared positive and negative test vectors
spec/                Wire format and JSON schemas
```

## Development

Every implementation consumes the same fixtures. A change to the binary format,
canonical model, or error behavior must update the shared contract first.

```bash
yarn install --frozen-lockfile
yarn run type-check
yarn run build
yarn run test:mocha
python -m unittest discover -s packages/python/tests -v
```

The complete PHP and .NET matrices run in GitHub Actions. See
[CONTRIBUTING.md](CONTRIBUTING.md) for the contribution workflow and
[ROADMAP.md](ROADMAP.md) for release gates.

## Credits and license

This repository is a fork of HearthSim's `hearthstone-deckstrings`. The original
history and attribution are preserved. Changes by Manacost Labs extend the
project with the shared contract and native backend implementations.

Licensed under the [ISC License](LICENSE).
