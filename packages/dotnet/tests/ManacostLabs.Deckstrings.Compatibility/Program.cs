using System.Text.Json;
using ManacostLabs.Deckstrings;

internal static class Program
{
    private static int Main(string[] args)
    {
        if (args.Length != 1)
        {
            Console.Error.WriteLine("Usage: compatibility <fixtures/deckstrings.json>");
            return 2;
        }

        using var document = JsonDocument.Parse(File.ReadAllText(args[0]));
        var checkedFixtures = 0;
        foreach (var fixture in document.RootElement.GetProperty("valid").EnumerateArray())
        {
            var name = fixture.GetProperty("name").GetString() ?? "unnamed";
            var deckstring = fixture.GetProperty("deckstring").GetString()
                ?? throw new InvalidOperationException($"{name} has no deckstring.");
            var canonicalDeckstring = fixture.TryGetProperty("canonicalDeckstring", out var canonical)
                ? canonical.GetString() ?? deckstring
                : deckstring;
            var expected = ParseDeck(fixture.GetProperty("deck"));
            var decoded = Deckstrings.Decode(deckstring);

            AssertDecksEqual(expected, decoded, $"{name} decode");
            AssertEqual(canonicalDeckstring, Deckstrings.Encode(expected), $"{name} encode");
            AssertEqual(canonicalDeckstring, Deckstrings.Encode(decoded), $"{name} round-trip");
            checkedFixtures++;
        }

        foreach (var fixture in document.RootElement.GetProperty("invalid").EnumerateArray())
        {
            var name = fixture.GetProperty("name").GetString() ?? "unnamed";
            var deckstring = fixture.GetProperty("deckstring").GetString() ?? string.Empty;
            var expectedCode = fixture.GetProperty("errorCode").GetString()
                ?? throw new InvalidOperationException($"{name} has no error code.");
            try
            {
                Deckstrings.Decode(deckstring);
                throw new InvalidOperationException($"{name} did not throw.");
            }
            catch (DeckstringException error)
            {
                AssertEqual(expectedCode, error.ErrorCode, $"{name} error code");
            }
            checkedFixtures++;
        }

        Console.WriteLine($".NET compatibility fixtures passed: {checkedFixtures}");
        return 0;
    }

    private static Deck ParseDeck(JsonElement element)
    {
        var deck = new Deck { Format = (DeckFormat)element.GetProperty("format").GetInt32() };
        foreach (var hero in element.GetProperty("heroes").EnumerateArray())
        {
            deck.Heroes.Add(hero.GetInt32());
        }
        foreach (var card in element.GetProperty("cards").EnumerateArray())
        {
            deck.Cards.Add(new DeckCard(card[0].GetInt32(), card[1].GetInt32()));
        }
        foreach (var card in element.GetProperty("sideboardCards").EnumerateArray())
        {
            deck.SideboardCards.Add(new SideboardCard(
                card[0].GetInt32(),
                card[1].GetInt32(),
                card[2].GetInt32()));
        }

        return deck;
    }

    private static void AssertDecksEqual(Deck expected, Deck actual, string name)
    {
        AssertEqual(expected.Format, actual.Format, $"{name} format");
        AssertSequence(
            expected.Heroes,
            actual.Heroes,
            $"{name} heroes");
        AssertSequence(
            expected.Cards.Select(card => (card.DbfId, card.Count)),
            actual.Cards.Select(card => (card.DbfId, card.Count)),
            $"{name} cards");
        AssertSequence(
            expected.SideboardCards.Select(card => (card.DbfId, card.Count, card.OwnerDbfId)),
            actual.SideboardCards.Select(card => (card.DbfId, card.Count, card.OwnerDbfId)),
            $"{name} sideboards");
    }

    private static void AssertSequence<T>(IEnumerable<T> expected, IEnumerable<T> actual, string name)
    {
        if (!expected.SequenceEqual(actual))
        {
            throw new InvalidOperationException($"{name} mismatch.");
        }
    }

    private static void AssertEqual<T>(T expected, T actual, string name)
    {
        if (!EqualityComparer<T>.Default.Equals(expected, actual))
        {
            throw new InvalidOperationException($"{name}: expected {expected}, got {actual}.");
        }
    }
}
