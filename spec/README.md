# Deckstring compatibility contract

This directory defines the shared behavior for every language package in this
repository. The original TypeScript implementation is the initial reference,
but the fixture suite is the long-term source of truth.

## Version 1 wire layout

Integers are unsigned varints unless explicitly described otherwise.

1. Reserved byte: `0x00`
2. Deckstring version: `1`
3. Format: Wild `1`, Standard `2`, Classic `3`, or Twist `4`
4. Hero count, followed by hero DBF IDs
5. Single-copy card count, followed by DBF IDs
6. Double-copy card count, followed by DBF IDs
7. N-copy card count, followed by `(DBF ID, count)` pairs
8. Sideboard marker: `0` or `1`
9. When the marker is `1`, three sideboard groups follow:
   - single-copy `(DBF ID, owner DBF ID)` entries
   - double-copy `(DBF ID, owner DBF ID)` entries
   - n-copy `(DBF ID, count, owner DBF ID)` entries

The resulting bytes are Base64 encoded.

Legacy deckstrings created before sideboards may end immediately after the main
card groups. Decoders must interpret a missing sideboard marker as `0`.

## Canonical representation

The common JSON representation is:

```json
{
  "format": 2,
  "heroes": [7],
  "cards": [[1, 2], [4, 1]],
  "sideboardCards": [[5, 1, 90749]]
}
```

- Cards are `[dbfId, count]` pairs.
- Sideboard cards are `[dbfId, count, ownerDbfId]` triplets.
- Heroes are sorted by DBF ID.
- Cards are sorted by DBF ID.
- Sideboard cards are sorted first by owner DBF ID and then by card DBF ID.
- `sideboardCards` is always present in decoded output, including when empty.
- All IDs and counts in canonical output are positive integers.

For backward compatibility, an encoder may temporarily accept zero-count input
and omit it. Zero-count entries are never canonical output and new APIs should
report them through validation.

## Golden fixtures

`fixtures/deckstrings.json` is consumed directly by every implementation. Each
valid fixture has a name, a canonical deck definition, and an input deckstring.
`canonicalDeckstring` is present only when legacy input canonicalizes to a
different output. A conforming implementation must:

1. decode the deckstring to the fixture's canonical deck definition;
2. encode the deck definition to `canonicalDeckstring` when present, otherwise
   to the fixture's input deckstring;
3. encode its own decoded result to that same canonical deckstring.

No implementation may maintain a private copy of the golden vectors.

## Stable error contract

Every public decoding error exposes a machine-readable `errorCode`/`code`
value in addition to a human-readable message. The shared values are:

- `invalid_input`
- `invalid_base64`
- `unexpected_end`
- `invalid_reserved`
- `unsupported_version`
- `unsupported_format`
- `invalid_varint`
- `invalid_id`
- `invalid_count`
- `invalid_sideboard`
- `trailing_data`
- `limit_exceeded`
- `invalid_deck`

`fixtures/deckstrings.json` contains the invalid inputs and the expected code.
Implementations may use idiomatic exception class and property names, but the
string value must match exactly. Error messages are explanatory and are not a
compatibility contract.

Decoders reject inputs larger than 1 MiB after Base64 decoding and item groups
larger than 10,000 entries. These are defensive limits, not valid Hearthstone
deck sizes.

Structured deck validation rejects models whose hero, card, and sideboard
arrays contain more than 30,000 items in total. This bounds work and the number
of validation errors even for malformed entries and legacy zero-count values.
Mapping-based implementations also fail early when an input model contains
more than 16 top-level properties, so unknown-property errors remain bounded.

## Validation API

`canonicalize(deck)` returns a new canonical deck and raises the package's
deckstring exception when the input is invalid. It never mutates caller-owned
arrays or objects.

`validate(deck)` never raises for ordinary invalid user data. It returns:

```json
{
  "valid": false,
  "errors": [
    {
      "code": "invalid_count",
      "path": "cards[0][1]",
      "message": "card count must be a non-negative integer"
    }
  ]
}
```

The normative shape is `validation-result.schema.json`. Language-specific
property casing may be idiomatic, but JSON serialization must match this shape.

Duplicate hero IDs, duplicate card DBF IDs, and duplicate sideboard
`(ownerDbfId, dbfId)` pairs are invalid. The library does not silently merge
duplicates because that can hide upstream data errors. This rule applies both
to caller-supplied deck models and duplicate IDs encoded in binary deckstrings;
decoders report `invalid_deck` for those payloads.

## Full clipboard exports

`parse_export`/`parseExport` accepts the full text copied by Hearthstone:

- lines beginning with `#` in column zero are metadata comments;
- the first `### name` line before the deckstring supplies the deck name;
- exactly one non-empty, non-comment line must contain the deckstring;
- CRLF, LF, and CR line endings are accepted;
- the returned deckstring is always canonical, including for legacy input;
- deck names and the deckstring are trimmed using the Unicode `White_Space`
  property (U+FEFF is deliberately excluded);
- comments are stored without the leading `#` and one optional following space;
  all other comment whitespace is preserved.

`format_export`/`formatExport` produces deterministic LF output. It writes the
name first, metadata comments next, then a `#` separator and the canonical
deckstring. Card display lines are optional presentation metadata supplied by
the caller; the core remains locale-neutral and does not fetch card data.

The normative parsed representation is `export.schema.json`; shared parse,
format, and resolver examples plus invalid inputs live in
`fixtures/exports.json`.

Clipboard export input is limited to 1,500,000 UTF-8 bytes before line
splitting. Larger input reports `limit_exceeded`; malformed Unicode reports
`invalid_input`.
