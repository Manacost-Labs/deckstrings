using ManacostLabs.Deckstrings;

var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

app.MapPost("/deckstrings/decode", DecodeDeck);
app.MapPost("/deckstrings/parse-export", ParseDeckExport);
app.MapGet("/deckstrings/example-export", FormatExampleExport);

app.Run();

static IResult DecodeDeck(DecodeRequest request)
{
    try
    {
        var deck = Deckstrings.Decode(request.Deckstring);
        return Results.Ok(new
        {
            deck = Deckstrings.ToTransport(deck),
            deckstring = Deckstrings.Encode(deck),
        });
    }
    catch (DeckstringException error)
    {
        return InvalidInput(error);
    }
}

static IResult ParseDeckExport(ExportRequest request)
{
    try
    {
        var parsed = Deckstrings.ParseExport(request.Text);
        object metadata = parsed.Metadata.Name == null
            ? new { comments = parsed.Metadata.Comments }
            : new { name = parsed.Metadata.Name, comments = parsed.Metadata.Comments };
        return Results.Ok(new
        {
            deck = Deckstrings.ToTransport(parsed.Deck),
            deckstring = parsed.Deckstring,
            metadata,
        });
    }
    catch (DeckstringException error)
    {
        return InvalidInput(error);
    }
}

static IResult FormatExampleExport()
{
    var deck = new Deck { Format = DeckFormat.Wild };
    deck.Heroes.Add(7);
    deck.Cards.Add(new DeckCard(1, 2));
    deck.SideboardCards.Add(new SideboardCard(5, 1, 90749));

    var metadata = new DeckExportMetadata { Name = "API example" };
    metadata.Comments.Add("Format: Wild");
    var cards = new Dictionary<int, CardDisplay>
    {
        [1] = new("First Card", 1),
        [5] = new("Sideboard Card"),
    };

    var text = Deckstrings.FormatExport(
        deck,
        metadata,
        dbfId => cards.TryGetValue(dbfId, out var card) ? card : null);
    return Results.Text(text, "text/plain; charset=utf-8");
}

static IResult InvalidInput(DeckstringException error)
{
    return Results.UnprocessableEntity(new
    {
        error = new
        {
            code = error.ErrorCode,
            message = "The deck input is invalid.",
        },
    });
}

internal sealed record DecodeRequest(string Deckstring);

internal sealed record ExportRequest(string Text);
