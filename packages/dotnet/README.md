# Manacost Labs Hearthstone Deckstrings for .NET

A dependency-free .NET implementation of the shared deckstring contract in
this repository. The library targets `netstandard2.0` and `net8.0`.

```csharp
using ManacostLabs.Deckstrings;

var deck = Deckstrings.Decode("AAEBAQcBBAMBAgMAAA==");
var deckstring = Deckstrings.Encode(deck);
```

Invalid input raises `DeckstringException`. Its `ErrorCode` property follows
the shared error contract in `../../spec/README.md`; callers should not match
the human-readable message.

This package is under active development and has not been published to NuGet
yet.
