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

## Shared JSON transport

`Deck` remains the idiomatic .NET model. Use `DeckTransport` at HTTP and JSON
boundaries when the exact cross-language schema is required. It exposes numeric
`Format`, `Heroes`, `[dbfId, count]` card arrays, and
`[dbfId, count, ownerDbfId]` sideboard arrays. `ToTransport` canonicalizes the
deck; `FromTransport` validates the tuple shape and returns a canonical `Deck`.

```csharp
using System.Text.Json;
using ManacostLabs.Deckstrings;

var options = new JsonSerializerOptions
{
    PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
};

var transport = Deckstrings.ToTransport(deck);
var json = JsonSerializer.Serialize(transport, options);
// {"format":1,"heroes":[7],"cards":[[1,2],[2,2],[3,2],[4,1]],"sideboardCards":[]}

var input = JsonSerializer.Deserialize<DeckTransport>(json, options)
    ?? throw new InvalidOperationException("Missing deck JSON.");
var restored = Deckstrings.FromTransport(input);
```

Project validation in the same way. `ValidationResultTransport` and
`ValidationErrorTransport` expose the exact `valid`, `errors`, `code`, `path`,
and `message` shape when the same camel-case policy is used:

```csharp
var validation = Deckstrings.ToTransport(Deckstrings.Validate(restored));
var validationJson = JsonSerializer.Serialize(validation, options);
```

The library itself does not reference `System.Text.Json`; applications may use
their serializer of choice as long as public property names are emitted in
camel case. Configure unknown-property rejection in that serializer when raw
JSON must satisfy `additionalProperties: false`.

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
