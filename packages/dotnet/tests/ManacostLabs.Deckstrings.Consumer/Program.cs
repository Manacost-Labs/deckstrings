using ManacostLabs.Deckstrings;

var parsed = Deckstrings.ParseExport(
    "### Consumer smoke\n" +
    "# restored from a packed NuGet artifact\n" +
    "AAEBAQcBBAMBAgMAAA==");

if (!Deckstrings.Validate(parsed.Deck).IsValid)
{
    throw new InvalidOperationException("Packed library rejected a known-good deck.");
}

var formatted = Deckstrings.FormatExport(
    parsed.Deck,
    parsed.Metadata,
    dbfId => dbfId == 1 ? new CardDisplay("Example card", 1) : null);

if (!formatted.Contains("# 2x (1) Example card", StringComparison.Ordinal) ||
    !string.Equals(parsed.Deckstring, Deckstrings.Encode(parsed.Deck), StringComparison.Ordinal))
{
    throw new InvalidOperationException("Packed library consumer smoke test failed.");
}

Console.WriteLine("Packed ManacostLabs.Deckstrings consumer smoke test passed.");
