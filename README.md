# Manacost Labs Hearthstone Deckstrings

[![CI](https://github.com/Manacost-Labs/deckstrings/actions/workflows/ci.yml/badge.svg)](https://github.com/Manacost-Labs/deckstrings/actions/workflows/ci.yml)
[![CodeQL](https://github.com/Manacost-Labs/deckstrings/actions/workflows/codeql.yml/badge.svg)](https://github.com/Manacost-Labs/deckstrings/actions/workflows/codeql.yml)
[![npm](https://img.shields.io/npm/v/@manacost-labs/deckstrings)](https://www.npmjs.com/package/@manacost-labs/deckstrings)
[![PyPI](https://img.shields.io/pypi/v/manacost-deckstrings)](https://pypi.org/project/manacost-deckstrings/)
[![NuGet](https://img.shields.io/nuget/v/ManacostLabs.Deckstrings)](https://www.nuget.org/packages/ManacostLabs.Deckstrings)
[![Packagist](https://img.shields.io/packagist/v/manacost-labs/hearthstone-deckstrings)](https://packagist.org/packages/manacost-labs/hearthstone-deckstrings)
[![License: ISC](https://img.shields.io/badge/license-ISC-blue.svg)](LICENSE)

A dependency-free Hearthstone deckstring backend library for JavaScript,
TypeScript, PHP, Python, and .NET. All four implementations share one public
contract and the same golden fixtures, including sideboards and full clipboard
exports.

## Install

| Ecosystem | Package | Supported runtime |
| --- | --- | --- |
| npm | `npm install @manacost-labs/deckstrings` | Node.js 22 or 24+, modern browsers |
| Composer | `composer require manacost-labs/hearthstone-deckstrings` | PHP 8.2–8.5 |
| PyPI | `python -m pip install manacost-deckstrings` | Python 3.10–3.14 |
| NuGet | `dotnet add package ManacostLabs.Deckstrings` | `netstandard2.0`, .NET 8, .NET 10 |

Package versions advance together. Version `1.0.0` defines the first stable
cross-language API.

## What the library owns

- version 1 deckstring encoding and decoding;
- Wild, Standard, Classic, and Twist formats;
- heroes, cards, and sideboards;
- deterministic canonical ordering;
- structured validation and stable error codes;
- parsing and formatting complete Hearthstone clipboard exports;
- defensive limits for untrusted input.

The core does not download card data, make network requests, or decide whether
a deck is legal for a patch. Card names and costs can be added at the edge with
an optional resolver callback.

## Shared model

```json
{
  "format": 1,
  "heroes": [7],
  "cards": [[1, 2], [2, 2], [3, 2], [4, 1]],
  "sideboardCards": [[5, 1, 90749]]
}
```

- `cards` entries are `[dbfId, count]`;
- `sideboardCards` entries are `[dbfId, count, ownerDbfId]`;
- heroes and cards are sorted by DBF ID;
- sideboard cards are sorted by owner and then DBF ID;
- duplicate heroes, cards, and sideboard `(ownerDbfId, dbfId)` pairs are invalid.

The normative model is [spec/deck.schema.json](spec/deck.schema.json), and the
wire/error/export contract is documented in [spec/README.md](spec/README.md).

## JavaScript / TypeScript

```ts
import {
  FormatType,
  canonicalize,
  decode,
  encode,
  formatExport,
  parseExport,
  validate,
} from "@manacost-labs/deckstrings";

const deck = decode("AAEBAQcBBAMBAgMAAA==");
const result = validate(deck); // { valid, errors }
const canonical = canonicalize(deck);
const deckstring = encode(canonical);
const parsed = parseExport(`### Example\n${deckstring}`);
const text = formatExport(parsed.deck, parsed.metadata);
```

The npm package includes ESM, CommonJS, browser ESM, UMD, and bundled
TypeScript declarations.

## PHP

```php
use ManacostLabs\Deckstrings\Deckstrings;

$deck = Deckstrings::decode('AAEBAQcBBAMBAgMAAA==');
$result = Deckstrings::validate($deck);
$deckstring = Deckstrings::encode(Deckstrings::canonicalize($deck));
$parsed = Deckstrings::parseExport("### Example\n{$deckstring}");
$text = Deckstrings::formatExport($parsed['deck'], $parsed['metadata']);
```

## Python

```python
from manacost_deckstrings import (
    canonicalize,
    decode,
    encode,
    format_export,
    parse_export,
    validate,
)

deck = decode("AAEBAQcBBAMBAgMAAA==")
result = validate(deck)
deckstring = encode(canonicalize(deck))
parsed = parse_export(f"### Example\n{deckstring}")
text = format_export(parsed["deck"], parsed["metadata"])
```

The Python distribution is typed and ships a `py.typed` marker.

## C# / .NET

```csharp
using ManacostLabs.Deckstrings;

var deck = Deckstrings.Decode("AAEBAQcBBAMBAgMAAA==");
var result = Deckstrings.Validate(deck);
var deckstring = Deckstrings.Encode(Deckstrings.Canonicalize(deck));
var parsed = Deckstrings.ParseExport($"### Example\n{deckstring}");
var text = Deckstrings.FormatExport(parsed.Deck, parsed.Metadata);
```

NuGet releases include XML documentation, portable PDBs, Source Link metadata,
and a separate `.snupkg` symbol package.

## Validation and errors

`validate`/`Validate` returns ordinary user-input failures and does not throw:

```json
{
  "valid": false,
  "errors": [
    {
      "code": "invalid_count",
      "path": "cards[0][1]",
      "message": "card count must be a positive integer"
    }
  ]
}
```

Encoding, decoding, canonicalization, and export parsing raise an idiomatic
language exception. Match its stable machine-readable code, not the
human-readable message. See [docs/API.md](docs/API.md) for language-specific
names and the complete code list.

## Card display resolver

`formatExport`/`format_export` accepts an optional callback from DBF ID to
`{ name, cost? }` (or the native equivalent). The callback may return `null`
for an unknown card. Names must be non-blank single-line strings, and costs
must be non-negative integers no larger than `2,147,483,647`. The resolver is
presentation-only and never changes the encoded deckstring.

## Compatibility promise

Every implementation reads [fixtures/deckstrings.json](fixtures/deckstrings.json),
[fixtures/api.json](fixtures/api.json), and [fixtures/exports.json](fixtures/exports.json)
directly. A behavior change is not accepted until the shared contract and all
language jobs agree. Legacy deckstrings without a sideboard marker remain
supported; encoders always produce canonical output.

## Development

```bash
# JavaScript / TypeScript
yarn install --frozen-lockfile --ignore-scripts
npx playwright install chromium
npm run verify

# Shared schemas
uv sync --project packages/python --locked --all-extras
uv run --project packages/python --locked python scripts/validate_fixtures.py
uv run --project packages/python --locked python scripts/check_versions.py

# PHP
composer install --no-scripts --no-plugins
composer check

# Python
uv run --project packages/python --locked pytest packages/python/tests
uv run --project packages/python --locked ruff check packages/python
uv run --project packages/python --locked mypy packages/python/src

# .NET
dotnet test packages/dotnet/tests/ManacostLabs.Deckstrings.Tests/ManacostLabs.Deckstrings.Tests.csproj -c Release
```

See [CONTRIBUTING.md](CONTRIBUTING.md), [the release process](docs/RELEASING.md),
[the migration guide](docs/MIGRATION.md), and [the roadmap](ROADMAP.md).

## Credits and license

This is an independent Manacost Labs repository whose complete Git history is
derived from and preserves attribution to
[HearthSim/hearthstone-deckstrings](https://github.com/HearthSim/hearthstone-deckstrings).
Manacost Labs maintains the multi-language contract, native backend
implementations, packaging, and release automation. Repository migration details
are recorded in [docs/REPOSITORY_MIGRATION.md](docs/REPOSITORY_MIGRATION.md).

Licensed under the [ISC License](LICENSE).
