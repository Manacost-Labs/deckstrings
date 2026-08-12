# Migrating to 1.0

Version 1.0 publishes the shared deckstring contract under Manacost Labs package
coordinates. JavaScript users migrating from the upstream-compatible
`deckstrings` 3.x package must change the package name. PHP, Python, and .NET
users migrating from repository snapshots or prereleases should also review the
stricter validation and runtime baselines below.

## Package coordinates

| Ecosystem | Install |
| --- | --- |
| npm | `npm install @manacost-labs/deckstrings@^1.0.0` |
| Composer | `composer require manacost-labs/hearthstone-deckstrings:^1.0` |
| PyPI | `python -m pip install "manacost-deckstrings~=1.0"` |
| NuGet | `dotnet add package ManacostLabs.Deckstrings --version 1.0.0` |

The release process keeps version `1.0.0` synchronized across all four package
coordinates. It is a new Manacost Labs distribution identity; its version does
not continue the npm version number of the upstream `deckstrings` package.
Run the install commands only after the corresponding registry smoke test in
[`RELEASING.md`](RELEASING.md#registry-smoke-tests) has passed.

## JavaScript package rename

Replace the dependency:

```diff
- "deckstrings": "^3.1.2"
+ "@manacost-labs/deckstrings": "^1.0.0"
```

Replace imports without changing the basic `decode` and `encode` calls:

```diff
- import { decode, encode, FormatType } from "deckstrings";
+ import { decode, encode, FormatType } from "@manacost-labs/deckstrings";
```

CommonJS remains supported:

```diff
- const { decode, encode } = require("deckstrings");
+ const { decode, encode } = require("@manacost-labs/deckstrings");
```

Browser-specific ESM consumers may import
`@manacost-labs/deckstrings/browser`. The UMD entry point is
`@manacost-labs/deckstrings/browser.umd` and exposes
`globalThis.ManacostDeckstrings`.

The Node.js baseline is now `^22.0.0` or `>=24.0.0`. Update production and CI
runtimes before changing the dependency.

## Runtime baselines

- PHP: 8.2–8.5.
- Python: 3.10–3.14.
- .NET: `netstandard2.0`, `net8.0`, or `net10.0`.

Do not infer support from a successful install on an older runtime; these are
the tested package contracts.

## Canonical model changes

Every decoder now returns the same canonical shape:

```json
{
  "format": 1,
  "heroes": [7],
  "cards": [[1, 2], [4, 1]],
  "sideboardCards": []
}
```

Check callers for these changes:

- `sideboardCards` is always present on decoded and canonical output, even when
  empty.
- Heroes and main-deck cards are sorted by DBF ID. Sideboard cards are sorted
  by owner DBF ID, then card DBF ID.
- `encode` and `canonicalize` return canonical output without mutating the
  supplied model.
- Duplicate heroes, duplicate main-deck DBF IDs, and duplicate sideboard
  `(ownerDbfId, dbfId)` pairs are rejected instead of being merged.
- JavaScript, PHP, and Python mapping inputs reject unknown deck properties as
  `invalid_deck`. The .NET package accepts a typed `Deck`; configure the JSON
  serializer to reject unmapped properties at the HTTP/deserialization
  boundary when strict raw JSON is required.
- New input must use positive counts. `canonicalize` and `encode` still omit
  legacy zero-count entries, while `validate` reports them.
- IDs and counts must be integers no larger than `2,147,483,647`.

If application logic depends on the original order of input arrays, keep that
order in a separate presentation model. Do not use decoded deck order as UI
state.

## Validation and errors

Use the new non-throwing validation API when accepting structured deck JSON:

```ts
const result = validate(candidate);
if (!result.valid) {
  return { status: 422, errors: result.errors };
}
```

The equivalent functions are `Deckstrings::validate` in PHP, `validate` in
Python, and `Deckstrings.Validate` in .NET.

Codec and canonicalization failures now expose a stable string code. Replace
message matching with the idiomatic property:

| Ecosystem | Stable code |
| --- | --- |
| JavaScript/TypeScript | `DeckstringError.code` |
| PHP | `DeckstringException::getErrorCode()` |
| Python | `DeckstringError.code` |
| .NET | `DeckstringException.ErrorCode` |

For example:

```diff
- if (String(error).includes("Base64")) { /* ... */ }
+ if (error instanceof DeckstringError && error.code === "invalid_base64") {
+   /* ... */
+ }
```

Messages remain human-readable but are not versioned API. See
[`API.md`](API.md#stable-errors) for the complete code list.

## Stricter untrusted-input handling

Version 1.0 uses strict Base64 parsing, rejects malformed or oversized varints,
rejects trailing binary data, and caps decoded input at 1 MiB and each item
group at 10,000 entries. Existing code that accepted whitespace, URL-safe
Base64, invalid length or missing required padding, or concatenated data must
normalize or reject that input before calling `decode`.

Do not retry another parser after a limit error. Treat `limit_exceeded` as a
final rejection at the request boundary.

## Clipboard exports

Applications no longer need to extract a deckstring with a regular expression.
Use the full-export APIs so metadata and legacy deckstrings are handled
consistently:

| Ecosystem | Parse | Format |
| --- | --- | --- |
| JavaScript/TypeScript | `parseExport(text)` | `formatExport(deck, metadata?, resolver?)` |
| PHP | `Deckstrings::parseExport($text)` | `Deckstrings::formatExport($deck, $metadata, $resolver)` |
| Python | `parse_export(text)` | `format_export(deck, metadata, resolver)` |
| .NET | `Deckstrings.ParseExport(text)` | `Deckstrings.FormatExport(deck, metadata, resolver)` |

Portable metadata consists only of an optional `name` and a `comments` list.
For every parsed comment line, exactly one leading `#` and one optional space
are removed. Comment content may itself start with `#`; the formatter adds its
own marker. Names, comments, and resolver names must be single-line text. After
the first deck name, another `### Subtitle` line before the deckstring is
preserved as comment content `## Subtitle`.

The card resolver is optional and synchronous. It receives a DBF ID and returns
a name plus an optional non-negative cost, or no result. Keep the card catalog
outside the codec and preload it before formatting:

```ts
const cards = new Map([[1, { name: "Example Card", cost: 1 }]]);
const text = formatExport(deck, { name: "Example" }, (id) => cards.get(id));
```

Resolver output affects comment lines only; it cannot change the encoded deck.

## Migrating from `python-hearthstone`

The [`hearthstone` package](https://github.com/HearthSim/python-hearthstone) is
a broader toolkit: in addition to
`hearthstone.deckstrings`, it provides enums, card-definition readers, DBF
helpers, and a log parser. `manacost-deckstrings` replaces only its deckstring
codec. Keep `hearthstone` installed if the application still uses those other
modules or the optional card data package.

Replace the codec import and object-property API:

```diff
- from hearthstone.deckstrings import Deck
- from hearthstone.enums import FormatType
+ from manacost_deckstrings import decode, encode

- deck = Deck.from_deckstring(deckstring)
- assert deck.format == FormatType.FT_WILD
- canonical_deckstring = deck.as_deckstring
+ deck = decode(deckstring)
+ assert deck["format"] == 1
+ canonical_deckstring = encode(deck)
```

The models differ even though both use DBF IDs:

| `python-hearthstone` | `manacost-deckstrings` |
| --- | --- |
| mutable `Deck` instance | JSON-compatible typed dictionary |
| `deck.format` as `FormatType` | `deck["format"]` as integer `1`–`4` |
| `deck.heroes` | `deck["heroes"]` |
| `deck.cards` with tuples | `deck["cards"]` with two-item lists |
| `deck.sideboards` with tuples | `deck["sideboardCards"]` with three-item lists |
| `deck.as_deckstring` property | `encode(deck)` function |

To migrate an existing in-memory `hearthstone.deckstrings.Deck`, project it
explicitly and validate it before encoding:

```python
from hearthstone.deckstrings import Deck as LegacyDeck
from manacost_deckstrings import encode, validate

legacy = LegacyDeck.from_deckstring(input_deckstring)
candidate = {
    "format": int(legacy.format),
    "heroes": list(legacy.heroes),
    "cards": [list(card) for card in legacy.cards],
    "sideboardCards": [list(card) for card in legacy.sideboards],
}

result = validate(candidate)
if not result["valid"]:
    raise ValueError(result["errors"])

canonical_deckstring = encode(candidate)
```

The new decoder is deliberately stricter than the legacy implementation. It
requires strict padded Base64, rejects duplicate IDs and trailing bytes, bounds
varints and collection sizes, and reports a stable `DeckstringError.code`.
Run stored deckstrings through `decode` during rollout rather than assuming
that every value accepted by the old parser remains valid.

For complete clipboard text, use `parse_export` instead of first extracting a
Base64 line yourself:

```python
from manacost_deckstrings import parse_export

parsed = parse_export(clipboard_text)
deck = parsed["deck"]
deck_name = parsed["metadata"].get("name")
canonical_deckstring = parsed["deckstring"]
```

Card names, costs, set rotation, and legality still belong to a separate card
catalog. Pass preloaded card data to `format_export` through its resolver when
human-readable card lines are required.

## Migrating from `HearthDb`

[`HearthDb`](https://github.com/HearthSim/HearthDb) combines deck serialization
with a Hearthstone card database,
generated card IDs, and game enums. `ManacostLabs.Deckstrings` is intentionally
only a dependency-free codec. Keep `HearthDb` (or another card catalog) if the
application needs `Cards`, localized names, costs, sets, or collectible-card
lookups.

For direct decoding and encoding, replace `DeckSerializer`:

```diff
- using HearthDb.Deckstrings;
+ using ManacostLabs.Deckstrings;

- var deck = DeckSerializer.Deserialize(deckstring);
- var canonicalDeckstring = DeckSerializer.Serialize(deck, includeComments: false);
+ var deck = Deckstrings.Decode(deckstring);
+ var canonicalDeckstring = Deckstrings.Encode(deck);
```

The native object models are not assignment-compatible:

| `HearthDb.Deckstrings.Deck` | `ManacostLabs.Deckstrings.Deck` |
| --- | --- |
| one `HeroDbfId` | `Heroes` collection |
| `CardDbfIds` dictionary | `Cards` collection of `DeckCard` |
| nested `Sideboards` dictionaries | flat `SideboardCards` collection |
| `HearthDb.Enums.FormatType` | `DeckFormat` |
| `Name`, `DeckId`, `ZodiacYear` | not part of the binary deck model |

An explicit conversion keeps that boundary visible:

```csharp
using System;
using HearthDb.Deckstrings;
using ManacostLabs.Deckstrings;
using NewDeck = ManacostLabs.Deckstrings.Deck;
using NewDeckstrings = ManacostLabs.Deckstrings.Deckstrings;

static NewDeck ConvertDeck(HearthDb.Deckstrings.Deck source)
{
    var target = new NewDeck { Format = (DeckFormat)(int)source.Format };
    target.Heroes.Add(source.HeroDbfId);

    foreach (var card in source.CardDbfIds)
        target.Cards.Add(new DeckCard(card.Key, card.Value));

    foreach (var sideboard in source.Sideboards)
        foreach (var card in sideboard.Value)
            target.SideboardCards.Add(
                new SideboardCard(card.Key, card.Value, sideboard.Key));

    return target;
}

var legacy = DeckSerializer.Deserialize(input);
var deck = ConvertDeck(legacy);
var validation = NewDeckstrings.Validate(deck);
if (!validation.IsValid)
    throw new InvalidOperationException(validation.Errors[0].Code);

var canonicalDeckstring = NewDeckstrings.Encode(deck);
```

Treat `Name`, `DeckId`, and `ZodiacYear` separately. A name can be carried in
`DeckExportMetadata.Name`; `DeckId` and `ZodiacYear` are application metadata
and are not encoded by the shared deckstring format. Use `ParseExport` when the
input may contain a full clipboard export instead of relying on
`DeckSerializer.Deserialize` to combine card data and clipboard parsing.

To keep HearthDb card display data while using the new formatter, adapt it at
the resolver boundary:

```csharp
using HearthDb;
using ManacostLabs.Deckstrings;

CardDisplay? ResolveCard(int dbfId)
{
    var card = Cards.GetFromDbfId(dbfId);
    return card is null ? null : new CardDisplay(card.Name, card.Cost);
}

var metadata = new DeckExportMetadata { Name = legacy.Name };
var clipboardText = Deckstrings.FormatExport(deck, metadata, ResolveCard);
```

Unlike HearthDb serialization, the core codec does not require a DBF ID to
exist in a bundled card database and does not decide whether a deck is legal.
It validates the binary/model contract, reports stable error codes, and leaves
catalog and patch-specific rules to the application.

## Suggested rollout

1. Upgrade CI and production runtimes.
2. Change the package coordinate and import/namespace names.
3. Add `validate` at structured-input boundaries.
4. Catch failures by stable code, not message.
5. Update code that assumes `sideboardCards` may be absent or preserves input
   ordering.
6. Replace custom clipboard parsing with `parseExport`/`parse_export`.
7. Run a known production deck through `encode(decode(value))` and compare the
   result with the canonical value expected by the application.
8. Test one invalid Base64 input, one duplicate card, and one sideboard deck in
   the real request path before rollout.

The shared fixtures in [`fixtures/`](../fixtures/) are suitable for cross-language
contract tests. A canonical result may differ from a legacy input string while
still representing the same deck; store the returned canonical deckstring after
a successful migration.
