# API reference

Manacost Labs Hearthstone Deckstrings implements the same synchronous,
dependency-free contract in JavaScript/TypeScript, PHP, Python, and .NET. It
encodes version 1 Hearthstone deckstrings; it does not download card data or
check whether a deck is legal for a game mode.

## Packages and runtimes

| Ecosystem | Package | Supported runtime |
| --- | --- | --- |
| npm | `@manacost-labs/deckstrings` | Node.js `^22.0.0` or `>=24.0.0`; modern browsers |
| Composer | `manacost-labs/hearthstone-deckstrings` | PHP 8.2–8.5 |
| PyPI | `manacost-deckstrings` | Python 3.10–3.14 |
| NuGet | `ManacostLabs.Deckstrings` | `netstandard2.0`, `net8.0`, `net10.0` |

All examples below use package version `1.0.0`.

## Shared deck model

The JSON-compatible representation is:

```json
{
  "format": 1,
  "heroes": [7],
  "cards": [[1, 2], [4, 1]],
  "sideboardCards": [[5, 1, 90749]]
}
```

- `format` is Wild `1`, Standard `2`, Classic `3`, or Twist `4`.
- `heroes` contains positive integer hero DBF IDs.
- `cards` contains `[dbfId, count]` pairs.
- `sideboardCards` contains `[dbfId, count, ownerDbfId]` triplets. It may be
  omitted on input and is always present on decoded or canonical output.
- IDs and positive counts are limited to `2,147,483,647`.
- Hero IDs and main-deck card IDs must be unique. A sideboard entry is unique
  by `(ownerDbfId, dbfId)`.
- JavaScript, PHP, and Python mapping inputs reject properties other than
  `format`, `heroes`, `cards`, and `sideboardCards` as `invalid_deck`. The .NET
  API accepts a typed `Deck`, so unknown JSON-property handling belongs to the
  application's serializer boundary rather than `Deckstrings.Validate`.

Canonical output sorts heroes and main-deck cards by DBF ID. It sorts sideboard
cards by owner DBF ID and then card DBF ID. Public operations do not mutate
caller-owned objects or collections.

## Operations

### `decode`

Decodes a Base64 deckstring and returns a new canonical deck.

- Only wire-format version 1 and formats 1–4 are accepted.
- The standard Base64 alphabet with valid length and padding is required.
- Legacy inputs that end before the sideboard marker are accepted and
  canonicalize to an explicit empty sideboard.
- Decoded payloads larger than 1 MiB and item groups larger than 10,000 are
  rejected.
- Structured models with more than 30,000 total hero, card, and sideboard
  entries are rejected before per-item validation.
- The function throws the package's deckstring exception on failure.

### `encode`

Validates and canonicalizes a deck, then returns a canonical Base64 deckstring.
The same canonical deck produces the same string in every implementation.

For compatibility with older callers, `encode` and `canonicalize` accept
zero-count card entries and omit them. New input should not contain zero-count
entries; `validate` reports them as `invalid_count`.

### `canonicalize`

Returns a new canonical deck without encoding it. It sorts collections, adds an
empty `sideboardCards` collection when needed, and removes legacy zero-count
entries. Invalid input throws the package's deckstring exception with the code
of the first validation error.

### `validate`

Checks an in-memory deck without throwing for ordinary invalid user input. It
returns every issue in deterministic model order:

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

Use `validate` at an API boundary when all problems should be returned at once.
Use `canonicalize` or `encode` when fail-fast exception behavior is preferable.
Error messages are explanatory and may change; `code` and `path` are the
machine-readable contract.

### `parseExport` / `parse_export`

Parses a complete Hearthstone clipboard export and returns:

```json
{
  "deck": {
    "format": 1,
    "heroes": [7],
    "cards": [[1, 2]],
    "sideboardCards": []
  },
  "deckstring": "canonical Base64 deckstring",
  "metadata": {
    "name": "Optional deck name",
    "comments": ["Class: Warrior", "Format: Wild"]
  }
}
```

The parser accepts LF, CRLF, and CR line endings. A comment marker must be the
first character on its line. The first `### name` line
before the deckstring becomes `metadata.name`; later `###` lines before the
deckstring are ordinary comments. For every comment line, the parser removes
exactly one leading `#` and one optional following space. For example, a later
`### Subtitle` becomes comment content `## Subtitle`. Exactly one non-empty,
non-comment line must contain the deckstring. Deck names and the deckstring are
trimmed of surrounding whitespace; other comment whitespace is preserved. A
`###` name after the deckstring is invalid.
The returned deckstring is always canonical.

The complete clipboard text is limited to 1,500,000 UTF-8 bytes before line
splitting. Larger input reports `limit_exceeded`. Malformed Unicode input
reports `invalid_input` rather than leaking a runtime-specific encoding error.

Surrounding trimming uses the Unicode `White_Space` property exactly
(U+0009–U+000D, U+0020, U+0085, U+00A0, U+1680, U+2000–U+200A, U+2028,
U+2029, U+202F, U+205F, and U+3000). U+FEFF is not whitespace for this
contract and is therefore not removed.

Malformed export structure uses `invalid_input`. Errors from decoding the
embedded deckstring are preserved.

### `formatExport` / `format_export`

Formats a deck and optional metadata as deterministic LF text. Portable
metadata has two fields:

- `name`: optional, non-empty, single-line string;
- `comments`: optional list of single-line comment contents. A value may begin
  with `#`; the formatter always adds its own `# ` marker.

Thus comment content `## Subtitle` formats as `# ## Subtitle`. This preserves
the content of additional `###` lines returned by `parseExport`.

If any name, comment, or resolved card line is present, a `#` separator is
written before the canonical deckstring. With no metadata or resolved cards,
the result is the deckstring alone.

The optional synchronous card resolver has this shared contract:

```text
resolveCard(dbfId) -> { name: non-blank string, cost?: 32-bit non-negative integer } | null
```

Returning `null`/`None` omits the display line. A missing cost is formatted as
zero. Main-deck entries are emitted before sideboard entries:

```text
# 2x (3) Main Card
# 1x (0) Sideboard Card [sideboard:90749]
```

The resolver supplies presentation data only. It is not called by `decode` or
`parseExport`, does not affect the binary deckstring, and should not be used to
infer deck legality. Cache or preload remote card data before calling
`formatExport`; the API itself is deliberately synchronous and performs no
network access.

## JavaScript and TypeScript

```ts
import {
  DeckstringError,
  FormatType,
  canonicalize,
  decode,
  encode,
  formatExport,
  parseExport,
  validate,
  type CardResolver,
  type DeckDefinition,
  type ParsedExport,
} from "@manacost-labs/deckstrings";
```

| API | Signature |
| --- | --- |
| `decode` | `(deckstring: string) => Required<DeckDefinition>` |
| `encode` | `(deck: DeckDefinition) => string` |
| `canonicalize` | `(deck: DeckDefinition) => Required<DeckDefinition>` |
| `validate` | `(deck: unknown) => ValidationResult` |
| `parseExport` | `(text: unknown) => ParsedExport` |
| `formatExport` | `(deck, metadata?, resolveCard?) => string` |

`FormatType` exposes `FT_WILD`, `FT_STANDARD`, `FT_CLASSIC`, and `FT_TWIST`.
It is also exported as the backward-compatible numeric union type
`1 | 2 | 3 | 4`, so existing `import type { FormatType }` usages remain valid.
CommonJS consumers may use
`require("@manacost-labs/deckstrings")`. Browser ESM is available from
`@manacost-labs/deckstrings/browser`; the UMD entry point is
`@manacost-labs/deckstrings/browser.umd` and exposes
`globalThis.ManacostDeckstrings`.

Handle failures by class and code:

```ts
try {
  decode(userInput);
} catch (error) {
  if (error instanceof DeckstringError) {
    console.error(error.code);
  }
}
```

See the runnable [Node.js example](../examples/node/roundtrip.mjs).

## PHP

```php
use ManacostLabs\Deckstrings\Deckstrings;
use ManacostLabs\Deckstrings\DeckstringException;
```

| API | Signature |
| --- | --- |
| `Deckstrings::decode` | `(string $deckstring): array` |
| `Deckstrings::encode` | `(array $deck): string` |
| `Deckstrings::canonicalize` | `(array $deck): array` |
| `Deckstrings::validate` | `(mixed $deck): array` |
| `Deckstrings::parseExport` | `(string $text): array` |
| `Deckstrings::formatExport` | `(array $deck, array $metadata = [], ?callable $resolveCard = null): string` |

The resolver receives an integer DBF ID and returns
`['name' => string, 'cost' => int]` or `null`; `cost` may be omitted.

```php
try {
    $deck = Deckstrings::decode($userInput);
} catch (DeckstringException $error) {
    error_log($error->getErrorCode());
}
```

See the runnable [PHP example](../examples/php/roundtrip.php) and the
illustrative [Laravel controller](../examples/php/LaravelDeckController.php).

## Python

```python
from manacost_deckstrings import (
    DeckstringError,
    canonicalize,
    decode,
    encode,
    format_export,
    parse_export,
    validate,
)
```

| API | Signature |
| --- | --- |
| `decode` | `(deckstring: str) -> Deck` |
| `encode` | `(deck: Mapping[str, object]) -> str` |
| `canonicalize` | `(deck: Mapping[str, object]) -> Deck` |
| `validate` | `(deck: object) -> ValidationResult` |
| `parse_export` | `(text: str) -> ParsedExport` |
| `format_export` | `(deck, metadata=None, resolve_card=None) -> str` |

The package is typed and exports `Deck`, `DeckCard`, `SideboardCard`,
`ValidationIssue`, `ValidationResult`, `ExportMetadata`, `ParsedExport`,
`CardInfo`, and `CardResolver`.

```python
try:
    deck = decode(user_input)
except DeckstringError as error:
    print(error.code)
```

See the runnable [Python example](../examples/python/roundtrip.py) and the
illustrative [FastAPI app](../examples/python/fastapi_app.py).

## .NET

```csharp
using ManacostLabs.Deckstrings;
```

| API | Signature |
| --- | --- |
| `Deckstrings.Decode` | `(string deckstring) -> Deck` |
| `Deckstrings.Encode` | `(Deck deck) -> string` |
| `Deckstrings.Canonicalize` | `(Deck deck) -> Deck` |
| `Deckstrings.Validate` | `(Deck? deck) -> ValidationResult` |
| `Deckstrings.ParseExport` | `(string text) -> DeckExport` |
| `Deckstrings.FormatExport` | `(Deck deck, DeckExportMetadata? metadata = null, Func<int, CardDisplay?>? cardResolver = null) -> string` |

`ValidationResult.IsValid` and `ValidationResult.Errors` correspond to the
shared `valid` and `errors` fields. Each `ValidationError` exposes `Code`,
`Path`, and `Message`. `DeckFormat` defines `Wild`, `Standard`, `Classic`, and
`Twist`.

The library validates an already constructed `Deck`; it does not deserialize
JSON. Applications that accept raw JSON should configure their serializer to
reject unmapped properties before calling `Validate` (for example with
`JsonUnmappedMemberHandling.Disallow` on supported .NET versions).

The idiomatic .NET model uses `DeckCard` and `SideboardCard` classes, so its
default JSON serialization is not the tuple-array wire shape shown above.
Map it to an explicit transport DTO when exposing the shared JSON contract;
the ASP.NET example includes a `ToTransport` projection. Likewise, expose
`ValidationResult.IsValid` as the transport field `valid` when a JSON client
must consume the exact shared result shape.

```csharp
try
{
    var deck = Deckstrings.Decode(userInput);
}
catch (DeckstringException error)
{
    Console.Error.WriteLine(error.ErrorCode);
}
```

The resolver returns `new CardDisplay(name, cost)` or `null`. See the runnable
[ASP.NET minimal API example](../examples/dotnet/aspnet/Program.cs).

## Stable errors

| Code | Meaning |
| --- | --- |
| `invalid_input` | Missing input or invalid clipboard/export metadata |
| `invalid_base64` | The input is not strict Base64 |
| `unexpected_end` | Binary input ended before a required value |
| `invalid_reserved` | The reserved byte is not supported |
| `unsupported_version` | The wire-format version is not 1 |
| `unsupported_format` | The format is not Wild, Standard, Classic, or Twist |
| `invalid_varint` | A variable-length integer is malformed or out of range |
| `invalid_id` | A DBF ID is not a supported positive integer |
| `invalid_count` | A hero, item-group, or card count is invalid |
| `invalid_sideboard` | The binary sideboard marker or section is invalid |
| `trailing_data` | Bytes remain after the complete deck |
| `limit_exceeded` | A defensive size or item-group limit was exceeded |
| `invalid_deck` | The in-memory model is structurally invalid or contains duplicates |

The property containing this value is:

| Ecosystem | Exception and property |
| --- | --- |
| JavaScript/TypeScript | `DeckstringError.code` |
| PHP | `DeckstringException::getErrorCode()` |
| Python | `DeckstringError.code` |
| .NET | `DeckstringException.ErrorCode` |

Do not branch on exception messages. When exposing errors over HTTP, map the
stable code to your own status and public message; do not return stack traces.

## Compatibility contract

The schemas in [`spec/`](../spec/) and shared fixtures in
[`fixtures/`](../fixtures/) are normative. Card names, localized text, images,
rotations, and deck-legality rules intentionally remain outside this package.
