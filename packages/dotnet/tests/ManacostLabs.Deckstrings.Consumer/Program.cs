using System.Text.Json;
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

var jsonOptions = new JsonSerializerOptions
{
    PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
};
var deckTransport = Deckstrings.ToTransport(parsed.Deck);
var deckJson = JsonSerializer.Serialize(deckTransport, jsonOptions);
const string expectedDeckJson =
    "{\"format\":1,\"heroes\":[7],\"cards\":[[1,2],[2,2],[3,2],[4,1]],\"sideboardCards\":[]}";
var deserializedDeckTransport = JsonSerializer.Deserialize<DeckTransport>(deckJson, jsonOptions)
    ?? throw new InvalidOperationException("Deck transport JSON deserialized to null.");
if (!string.Equals(deckJson, expectedDeckJson, StringComparison.Ordinal) ||
    !string.Equals(
        Deckstrings.Encode(Deckstrings.FromTransport(deserializedDeckTransport)),
        parsed.Deckstring,
        StringComparison.Ordinal))
{
    throw new InvalidOperationException("Packed library deck transport contract failed.");
}

var missingCardsTransport = JsonSerializer.Deserialize<DeckTransport>(
    "{\"format\":1,\"heroes\":[7],\"sideboardCards\":[]}",
    jsonOptions) ?? throw new InvalidOperationException("Missing-cards transport JSON deserialized to null.");
try
{
    Deckstrings.FromTransport(missingCardsTransport);
    throw new InvalidOperationException("Packed library accepted a transport without required cards.");
}
catch (DeckstringException error) when (
    string.Equals(error.ErrorCode, DeckstringErrorCodes.InvalidDeck, StringComparison.Ordinal))
{
}

var invalidDeck = new Deck { Format = DeckFormat.Wild };
invalidDeck.Heroes.Add(7);
invalidDeck.Cards.Add(new DeckCard(1, 0));
var validationJson = JsonSerializer.Serialize(
    Deckstrings.ToTransport(Deckstrings.Validate(invalidDeck)),
    jsonOptions);
const string expectedValidationJson =
    "{\"valid\":false,\"errors\":[{\"code\":\"invalid_count\",\"path\":\"cards[0][1]\",\"message\":\"Card count must be positive.\"}]}";
if (!string.Equals(validationJson, expectedValidationJson, StringComparison.Ordinal))
{
    throw new InvalidOperationException("Packed library validation transport contract failed.");
}

Console.WriteLine("Packed ManacostLabs.Deckstrings consumer smoke test passed.");
