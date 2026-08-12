# Manacost Labs Hearthstone Deckstrings for .NET

A dependency-free .NET implementation of the shared deckstring contract in
this repository. The library targets `netstandard2.0` and `net8.0`.

```csharp
using ManacostLabs.Deckstrings;

var deck = Deckstrings.Decode("AAEBAQcBBAMBAgMAAA==");
var deckstring = Deckstrings.Encode(deck);
```

This package is under active development and has not been published to NuGet
yet.
