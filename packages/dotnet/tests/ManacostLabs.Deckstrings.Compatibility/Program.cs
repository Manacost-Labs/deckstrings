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

        var deckstringFixtures = Path.GetFullPath(args[0]);
        var fixtureDirectory = Path.GetDirectoryName(deckstringFixtures)
            ?? throw new InvalidOperationException("Fixture directory could not be resolved.");
        var checkedFixtures = CheckDeckstrings(deckstringFixtures);
        checkedFixtures += CheckApi(Path.Combine(fixtureDirectory, "api.json"));
        checkedFixtures += CheckExports(Path.Combine(fixtureDirectory, "exports.json"));

        Console.WriteLine($".NET compatibility fixtures passed: {checkedFixtures}");
        return 0;
    }

    private static int CheckDeckstrings(string path)
    {
        using var document = JsonDocument.Parse(File.ReadAllText(path));
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

        return checkedFixtures;
    }

    private static int CheckApi(string path)
    {
        using var document = JsonDocument.Parse(File.ReadAllText(path));
        var checkedFixtures = 0;
        foreach (var fixture in document.RootElement.GetProperty("canonicalize").EnumerateArray())
        {
            var name = fixture.GetProperty("name").GetString() ?? "unnamed";
            var deck = ParseDeck(fixture.GetProperty("deck"));
            if (fixture.TryGetProperty("expectedDeck", out var expectedElement))
            {
                AssertDecksEqual(
                    ParseDeck(expectedElement),
                    Deckstrings.Canonicalize(deck),
                    $"{name} canonicalize");
            }
            else
            {
                var expectedCode = fixture.GetProperty("errorCode").GetString()
                    ?? throw new InvalidOperationException($"{name} has no error code.");
                try
                {
                    Deckstrings.Canonicalize(deck);
                    throw new InvalidOperationException($"{name} did not throw.");
                }
                catch (DeckstringException error)
                {
                    AssertEqual(expectedCode, error.ErrorCode, $"{name} error code");
                }
            }
            checkedFixtures++;
        }

        foreach (var fixture in document.RootElement.GetProperty("validate").EnumerateArray())
        {
            var name = fixture.GetProperty("name").GetString() ?? "unnamed";
            var result = Deckstrings.Validate(ParseDeck(fixture.GetProperty("deck")));
            AssertEqual(fixture.GetProperty("valid").GetBoolean(), result.IsValid, $"{name} valid");

            var expectedErrors = fixture.GetProperty("errors").EnumerateArray().ToArray();
            AssertEqual(expectedErrors.Length, result.Errors.Count, $"{name} error count");
            for (var index = 0; index < expectedErrors.Length; index++)
            {
                AssertEqual(
                    expectedErrors[index].GetProperty("code").GetString(),
                    result.Errors[index].Code,
                    $"{name} error {index} code");
                AssertEqual(
                    expectedErrors[index].GetProperty("path").GetString(),
                    result.Errors[index].Path,
                    $"{name} error {index} path");
            }
            checkedFixtures++;
        }

        return checkedFixtures;
    }

    private static int CheckExports(string path)
    {
        using var document = JsonDocument.Parse(File.ReadAllText(path));
        var checkedFixtures = 0;
        foreach (var fixture in document.RootElement.GetProperty("valid").EnumerateArray())
        {
            var name = fixture.GetProperty("name").GetString() ?? "unnamed";
            var parsed = Deckstrings.ParseExport(
                fixture.GetProperty("text").GetString()
                    ?? throw new InvalidOperationException($"{name} has no text."));
            var expected = fixture.GetProperty("parsed");
            AssertDecksEqual(ParseDeck(expected.GetProperty("deck")), parsed.Deck, $"{name} deck");
            AssertEqual(
                expected.GetProperty("deckstring").GetString(),
                parsed.Deckstring,
                $"{name} deckstring");

            var expectedMetadata = expected.GetProperty("metadata");
            var expectedName = expectedMetadata.TryGetProperty("name", out var nameElement)
                ? nameElement.GetString()
                : null;
            AssertEqual(expectedName, parsed.Metadata.Name, $"{name} metadata name");
            AssertSequence(
                expectedMetadata.GetProperty("comments").EnumerateArray()
                    .Select(comment => comment.GetString() ?? string.Empty),
                parsed.Metadata.Comments,
                $"{name} metadata comments");
            AssertEqual(
                fixture.GetProperty("formatted").GetString(),
                Deckstrings.FormatExport(parsed.Deck, parsed.Metadata),
                $"{name} formatted export");
            checkedFixtures++;
        }

        foreach (var fixture in document.RootElement.GetProperty("invalid").EnumerateArray())
        {
            var name = fixture.GetProperty("name").GetString() ?? "unnamed";
            var expectedCode = fixture.GetProperty("errorCode").GetString()
                ?? throw new InvalidOperationException($"{name} has no error code.");
            try
            {
                Deckstrings.ParseExport(fixture.GetProperty("text").GetString() ?? string.Empty);
                throw new InvalidOperationException($"{name} did not throw.");
            }
            catch (DeckstringException error)
            {
                AssertEqual(expectedCode, error.ErrorCode, $"{name} error code");
            }
            checkedFixtures++;
        }

        var resolverFixtures = document.RootElement.GetProperty("resolver");
        foreach (var fixture in resolverFixtures.GetProperty("valid").EnumerateArray())
        {
            var name = fixture.GetProperty("name").GetString() ?? "unnamed";
            var cards = fixture.GetProperty("cards");
            var metadata = ParseMetadata(fixture.GetProperty("metadata"));
            var formatted = Deckstrings.FormatExport(
                ParseDeck(fixture.GetProperty("deck")),
                metadata,
                dbfId => ResolveCard(cards, dbfId));
            AssertEqual(
                fixture.GetProperty("formatted").GetString(),
                formatted,
                $"{name} resolver export");
            checkedFixtures++;
        }

        foreach (var fixture in resolverFixtures.GetProperty("invalid").EnumerateArray())
        {
            var name = fixture.GetProperty("name").GetString() ?? "unnamed";
            var cards = fixture.GetProperty("cards");
            var expectedCode = fixture.GetProperty("errorCode").GetString()
                ?? throw new InvalidOperationException($"{name} has no error code.");
            try
            {
                Deckstrings.FormatExport(
                    ParseDeck(fixture.GetProperty("deck")),
                    null,
                    dbfId => ResolveCard(cards, dbfId));
                throw new InvalidOperationException($"{name} did not throw.");
            }
            catch (DeckstringException error)
            {
                AssertEqual(expectedCode, error.ErrorCode, $"{name} error code");
            }
            checkedFixtures++;
        }

        return checkedFixtures;
    }

    private static DeckExportMetadata ParseMetadata(JsonElement element)
    {
        var metadata = new DeckExportMetadata();
        if (element.TryGetProperty("name", out var name))
        {
            metadata.Name = name.GetString();
        }
        foreach (var comment in element.GetProperty("comments").EnumerateArray())
        {
            metadata.Comments.Add(comment.GetString() ?? string.Empty);
        }
        return metadata;
    }

    private static CardDisplay? ResolveCard(JsonElement cards, int dbfId)
    {
        if (!cards.TryGetProperty(
                dbfId.ToString(System.Globalization.CultureInfo.InvariantCulture),
                out var card) ||
            card.ValueKind == JsonValueKind.Null)
        {
            return null;
        }

        var name = card.GetProperty("name").GetString()
            ?? throw new InvalidOperationException($"Resolver card {dbfId} has no name.");
        int? cost = card.TryGetProperty("cost", out var costElement)
            ? costElement.GetInt32()
            : null;
        return new CardDisplay(name, cost);
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
