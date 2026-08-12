using ManacostLabs.Deckstrings;
using Xunit;

namespace ManacostLabs.Deckstrings.Tests;

public sealed class DeckstringsTests
{
    [Fact]
    public void CanonicalizeReturnsSortedCopyAndPreservesCallerModel()
    {
        var deck = new Deck { Format = DeckFormat.Wild };
        deck.Heroes.Add(10);
        deck.Heroes.Add(2);
        deck.Cards.Add(new DeckCard(4, 1));
        deck.Cards.Add(new DeckCard(1, 0));
        deck.Cards.Add(new DeckCard(3, 2));
        deck.SideboardCards.Add(new SideboardCard(7, 1, 10));
        deck.SideboardCards.Add(new SideboardCard(5, 0, 2));
        deck.SideboardCards.Add(new SideboardCard(6, 2, 2));

        var canonical = Deckstrings.Canonicalize(deck);

        Assert.Equal(new[] { 2, 10 }, canonical.Heroes);
        Assert.Equal(new[] { (3, 2), (4, 1) }, canonical.Cards.Select(CardTuple));
        Assert.Equal(
            new[] { (6, 2, 2), (7, 1, 10) },
            canonical.SideboardCards.Select(SideboardTuple));
        Assert.Equal(new[] { 10, 2 }, deck.Heroes);
        Assert.Equal(3, deck.Cards.Count);
        Assert.Equal(3, deck.SideboardCards.Count);
    }

    [Fact]
    public void CanonicalizeRejectsDuplicateCards()
    {
        var deck = ValidDeck();
        deck.Cards.Add(new DeckCard(1, 1));
        deck.Cards.Add(new DeckCard(1, 2));

        var error = Assert.Throws<DeckstringException>(() => Deckstrings.Canonicalize(deck));

        Assert.Equal(DeckstringErrorCodes.InvalidDeck, error.ErrorCode);
    }

    [Fact]
    public void ValidateReturnsStructuredErrorsWithoutThrowing()
    {
        var deck = new Deck { Format = (DeckFormat)5 };
        deck.Heroes.Add(7);
        deck.Heroes.Add(7);
        deck.Cards.Add(new DeckCard(1, 0));

        var result = Deckstrings.Validate(deck);

        Assert.False(result.IsValid);
        Assert.Equal(
            new[]
            {
                (DeckstringErrorCodes.UnsupportedFormat, "format"),
                (DeckstringErrorCodes.InvalidDeck, "heroes[1]"),
                (DeckstringErrorCodes.InvalidCount, "cards[0][1]"),
            },
            result.Errors.Select(error => (error.Code, error.Path)));
        Assert.All(result.Errors, error => Assert.False(string.IsNullOrWhiteSpace(error.Message)));
    }

    [Fact]
    public void ValidateNullReturnsInvalidDeck()
    {
        var result = Deckstrings.Validate(null);

        Assert.False(result.IsValid);
        var error = Assert.Single(result.Errors);
        Assert.Equal(DeckstringErrorCodes.InvalidDeck, error.Code);
        Assert.Equal(string.Empty, error.Path);
    }

    [Fact]
    public void DeckTransportUsesCanonicalSharedTupleShapeAndRoundTrips()
    {
        var deck = new Deck { Format = DeckFormat.Wild };
        deck.Heroes.Add(10);
        deck.Heroes.Add(2);
        deck.Cards.Add(new DeckCard(4, 1));
        deck.Cards.Add(new DeckCard(3, 2));
        deck.SideboardCards.Add(new SideboardCard(7, 1, 10));
        deck.SideboardCards.Add(new SideboardCard(6, 2, 2));

        var transport = Deckstrings.ToTransport(deck);

        Assert.Equal(1, transport.Format);
        Assert.Equal(new[] { 2, 10 }, transport.Heroes);
        Assert.Equal(
            new[] { (3, 2), (4, 1) },
            transport.Cards.Select(card => (card[0], card[1])));
        Assert.Equal(
            new[] { (6, 2, 2), (7, 1, 10) },
            transport.SideboardCards.Select(card => (card[0], card[1], card[2])));

        var restored = Deckstrings.FromTransport(transport);
        Assert.Equal(new[] { 2, 10 }, restored.Heroes);
        Assert.Equal(new[] { (3, 2), (4, 1) }, restored.Cards.Select(CardTuple));
        Assert.Equal(
            new[] { (6, 2, 2), (7, 1, 10) },
            restored.SideboardCards.Select(SideboardTuple));
    }

    [Fact]
    public void FromTransportRejectsMalformedTupleWithStableCode()
    {
        var transport = new DeckTransport
        {
            Format = 1,
            Heroes = new[] { 7 },
            Cards = new[] { new[] { 1, 2, 3 } },
            SideboardCards = Array.Empty<int[]>(),
        };

        var error = Assert.Throws<DeckstringException>(
            () => Deckstrings.FromTransport(transport));

        Assert.Equal(DeckstringErrorCodes.InvalidDeck, error.ErrorCode);
    }

    [Theory]
    [InlineData(true)]
    [InlineData(false)]
    public void FromTransportRejectsMissingRequiredCardCollection(bool omitCards)
    {
        var transport = new DeckTransport
        {
            Format = 1,
            Heroes = new[] { 7 },
            Cards = omitCards ? null! : Array.Empty<int[]>(),
            SideboardCards = omitCards ? Array.Empty<int[]>() : null!,
        };

        var error = Assert.Throws<DeckstringException>(
            () => Deckstrings.FromTransport(transport));

        Assert.Equal(DeckstringErrorCodes.InvalidDeck, error.ErrorCode);
    }

    [Fact]
    public void ValidationTransportPreservesSharedFields()
    {
        var deck = ValidDeck();
        deck.Cards.Add(new DeckCard(1, 0));

        var transport = Deckstrings.ToTransport(Deckstrings.Validate(deck));

        Assert.False(transport.Valid);
        var error = Assert.Single(transport.Errors);
        Assert.Equal(DeckstringErrorCodes.InvalidCount, error.Code);
        Assert.Equal("cards[0][1]", error.Path);
        Assert.False(string.IsNullOrWhiteSpace(error.Message));
    }

    [Fact]
    public void ParseExportRejectsOversizedUtf8Text()
    {
        var error = Assert.Throws<DeckstringException>(
            () => Deckstrings.ParseExport(new string('\u00e9', 750001)));

        Assert.Equal(DeckstringErrorCodes.LimitExceeded, error.ErrorCode);
    }

    [Fact]
    public void ParseExportRejectsMalformedUnicodeWithStableCode()
    {
        var error = Assert.Throws<DeckstringException>(
            () => Deckstrings.ParseExport(new string(new[] { '\uD800' })));

        Assert.Equal(DeckstringErrorCodes.InvalidInput, error.ErrorCode);
    }

    [Fact]
    public void CardDisplayRejectsInvalidResolverDataWithStableCode()
    {
        var error = Assert.Throws<DeckstringException>(() => new CardDisplay("\u0085"));

        Assert.Equal(DeckstringErrorCodes.InvalidInput, error.ErrorCode);
    }

    [Fact]
    public void DecodeRejectsDuplicateIdsInBinaryInput()
    {
        var duplicateCardBytes = new byte[]
        {
            0, 1, 1, 1, 7,
            2, 1, 1,
            0,
            0,
            0,
        };

        var error = Assert.Throws<DeckstringException>(
            () => Deckstrings.Decode(Convert.ToBase64String(duplicateCardBytes)));

        Assert.Equal(DeckstringErrorCodes.InvalidDeck, error.ErrorCode);
    }

    [Fact]
    public void DecodeRejectsPayloadLargerThanOneMebibyte()
    {
        var payload = new byte[(1024 * 1024) + 1];

        var error = Assert.Throws<DeckstringException>(
            () => Deckstrings.Decode(Convert.ToBase64String(payload)));

        Assert.Equal(DeckstringErrorCodes.LimitExceeded, error.ErrorCode);
    }

    [Fact]
    public void ParseExportCanonicalizesLegacyDeckstringAndPreservesMetadata()
    {
        const string text =
            "# Generated externally\r\n" +
            "### Legacy deck\r\n" +
            "AAEBAQcBBAMBAgMA\r\n" +
            "# trailing";

        var parsed = Deckstrings.ParseExport(text);

        Assert.Equal("AAEBAQcBBAMBAgMAAA==", parsed.Deckstring);
        Assert.Equal("Legacy deck", parsed.Metadata.Name);
        Assert.Equal(new[] { "Generated externally", "trailing" }, parsed.Metadata.Comments);
    }

    [Fact]
    public void FormatExportUsesOptionalCardResolverForMainDeckAndSideboard()
    {
        var deck = ValidDeck();
        deck.Cards.Add(new DeckCard(1, 1));
        deck.Cards.Add(new DeckCard(2, 2));
        deck.SideboardCards.Add(new SideboardCard(5, 2, 10));
        var metadata = new DeckExportMetadata { Name = "Resolver deck" };
        metadata.Comments.Add("Format: Wild");

        var formatted = Deckstrings.FormatExport(
            deck,
            metadata,
            dbfId => dbfId switch
            {
                1 => new CardDisplay("First card", 3),
                5 => new CardDisplay("Sideboard card"),
                _ => null,
            });

        Assert.Equal(
            "### Resolver deck\n" +
            "# Format: Wild\n" +
            "# 1x (3) First card\n" +
            "# 2x (0) Sideboard card [sideboard:10]\n" +
            "#\n" +
            Deckstrings.Encode(deck),
            formatted);
    }

    [Fact]
    public void FormatExportRejectsMultilineMetadata()
    {
        var metadata = new DeckExportMetadata { Name = "unsafe\nname" };

        var error = Assert.Throws<DeckstringException>(
            () => Deckstrings.FormatExport(ValidDeck(), metadata));

        Assert.Equal(DeckstringErrorCodes.InvalidInput, error.ErrorCode);
    }

    [Fact]
    public void EncodeDecodeRoundTripIsCanonical()
    {
        var deck = ValidDeck();
        deck.Cards.Add(new DeckCard(4, 1));
        deck.Cards.Add(new DeckCard(1, 2));

        var deckstring = Deckstrings.Encode(deck);
        var decoded = Deckstrings.Decode(deckstring);

        Assert.Equal(deckstring, Deckstrings.Encode(decoded));
        Assert.Equal(new[] { (1, 2), (4, 1) }, decoded.Cards.Select(CardTuple));
    }

    private static Deck ValidDeck()
    {
        var deck = new Deck { Format = DeckFormat.Wild };
        deck.Heroes.Add(7);
        return deck;
    }

    private static (int DbfId, int Count) CardTuple(DeckCard card)
    {
        return (card.DbfId, card.Count);
    }

    private static (int DbfId, int Count, int OwnerDbfId) SideboardTuple(SideboardCard card)
    {
        return (card.DbfId, card.Count, card.OwnerDbfId);
    }
}
