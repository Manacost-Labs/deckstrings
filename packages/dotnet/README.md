# Manacost Labs Hearthstone Deckstrings for .NET

Dependency-free encoding, decoding, validation, and clipboard export support
for Hearthstone version 1 deckstrings. The same golden fixtures are used by the
JavaScript, PHP, Python, and .NET packages in this repository.

The NuGet package targets `netstandard2.0`, `net8.0`, and `net10.0`. It supports
modern .NET applications while retaining broad compatibility with runtimes
that implement .NET Standard 2.0.

## Install

```bash
dotnet add package ManacostLabs.Deckstrings --version 1.0.0
```

## Encode and decode

```csharp
using ManacostLabs.Deckstrings;

var deck = Deckstrings.Decode("AAEBAQcBBAMBAgMAAA==");
var canonicalDeckstring = Deckstrings.Encode(deck);
```

`Decode` accepts legacy deckstrings without a sideboard marker. `Encode` always
returns the canonical representation.

## Canonicalize and validate

`Canonicalize` returns a sorted copy and never mutates the caller-owned model.
It throws `DeckstringException` when the model cannot be canonicalized safely.

```csharp
var canonical = Deckstrings.Canonicalize(deck);
```

`Validate` is intended for ordinary user input and returns every discovered
problem without throwing:

```csharp
var result = Deckstrings.Validate(deck);
if (!result.IsValid)
{
    foreach (var error in result.Errors)
    {
        Console.WriteLine($"{error.Code} at {error.Path}: {error.Message}");
    }
}
```

Duplicate hero IDs, duplicate card IDs, and duplicate sideboard
`(ownerDbfId, dbfId)` pairs are invalid and are never merged silently. For
backward compatibility, `Canonicalize` and `Encode` omit legacy zero-count
entries; `Validate` reports them as `invalid_count`.

The package validates a typed `Deck` and does not deserialize JSON. If an API
must reject unknown JSON fields, configure that behavior in its serializer
before calling `Validate`.

`DeckCard` and `SideboardCard` are idiomatic classes rather than JSON tuples.
Project them to `[dbfId, count]` and `[dbfId, count, ownerDbfId]` transport
arrays when an HTTP API must expose the normative cross-language JSON shape;
see the repository ASP.NET example.

## Clipboard exports

Parse the complete text copied by Hearthstone while preserving the name and
comment metadata:

```csharp
var parsed = Deckstrings.ParseExport(clipboardText);

Console.WriteLine(parsed.Deckstring);          // always canonical
Console.WriteLine(parsed.Metadata.Name);
Console.WriteLine(parsed.Deck.Cards.Count);
```

Format deterministic LF output. An optional resolver can add localized card
display lines without coupling the codec to a card database or network API:

```csharp
var text = Deckstrings.FormatExport(
    parsed.Deck,
    parsed.Metadata,
    dbfId => cardDatabase.TryGetValue(dbfId, out var card)
        ? new CardDisplay(card.Name, card.Cost)
        : null);
```

The resolver is also called for sideboard cards; those lines include a
`[sideboard:ownerDbfId]` suffix.

## Error handling

Malformed deckstrings and invalid canonicalization input raise
`DeckstringException`. Match its stable `ErrorCode` property rather than its
human-readable `Message`:

```csharp
try
{
    Deckstrings.Decode("not-base64!");
}
catch (DeckstringException error) when (
    error.ErrorCode == DeckstringErrorCodes.InvalidBase64)
{
    // Ask the caller for another deckstring.
}
```

The shared error contract and defensive limits are documented in
[`../../spec/README.md`](../../spec/README.md).

## Package quality

Release builds enable nullable annotations, XML API documentation, .NET SDK
analyzers, deterministic compilation, Source Link metadata, package validation,
portable symbols, and `.snupkg` symbol packages. The NuGet package embeds this
README and repository metadata.

To verify the package from the repository root:

```bash
dotnet build packages/dotnet/src/ManacostLabs.Deckstrings/ManacostLabs.Deckstrings.csproj --configuration Release
dotnet test packages/dotnet/tests/ManacostLabs.Deckstrings.Tests/ManacostLabs.Deckstrings.Tests.csproj --configuration Release
dotnet run --project packages/dotnet/tests/ManacostLabs.Deckstrings.Compatibility/ManacostLabs.Deckstrings.Compatibility.csproj --configuration Release -- fixtures/deckstrings.json
dotnet pack packages/dotnet/src/ManacostLabs.Deckstrings/ManacostLabs.Deckstrings.csproj --configuration Release --no-build
dotnet run --project packages/dotnet/tests/ManacostLabs.Deckstrings.Consumer/ManacostLabs.Deckstrings.Consumer.csproj --configuration Release --framework net8.0
dotnet run --project packages/dotnet/tests/ManacostLabs.Deckstrings.Consumer/ManacostLabs.Deckstrings.Consumer.csproj --configuration Release --framework net10.0
```

The compatibility runner reads `deckstrings.json`, `api.json`, and
`exports.json` directly from the shared `fixtures` directory. The consumer
project references the packed NuGet artifact rather than the source project.

Licensed under the repository's ISC license.
