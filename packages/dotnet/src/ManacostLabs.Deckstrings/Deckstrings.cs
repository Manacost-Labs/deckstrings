using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;

namespace ManacostLabs.Deckstrings
{
    /// <summary>
    /// Encodes, decodes, validates, and formats Hearthstone deckstrings.
    /// </summary>
    public static class Deckstrings
    {
        private const int Version = 1;
        private const int MaxItemsPerGroup = 10000;
        private const int MaxItemsPerDeck = 30000;
        private const int MaxBase64Length = 1398104;
        private const int MaxDecodedLength = 1048576;
        private const int MaxExportUtf8Length = 1500000;

        /// <summary>
        /// Encodes a deck into its canonical version 1 deckstring.
        /// </summary>
        /// <param name="deck">The deck to encode.</param>
        /// <returns>The canonical Base64 deckstring.</returns>
        /// <exception cref="DeckstringException">The deck does not satisfy the shared contract.</exception>
        public static string Encode(Deck deck)
        {
            if (deck == null)
            {
                throw new DeckstringException(
                    DeckstringErrorCodes.InvalidDeck,
                    "Deck cannot be null.");
            }

            var canonical = Canonicalize(deck);
            using (var stream = new MemoryStream())
            {
                stream.WriteByte(0);
                WriteVarint(stream, Version);
                WriteVarint(stream, (int)canonical.Format);
                WriteVarint(stream, canonical.Heroes.Count);
                foreach (var hero in canonical.Heroes)
                {
                    WriteVarint(stream, hero);
                }

                WriteCardGroup(stream, canonical.Cards.Where(card => card.Count == 1), false);
                WriteCardGroup(stream, canonical.Cards.Where(card => card.Count == 2), false);
                WriteCardGroup(stream, canonical.Cards.Where(card => card.Count > 2), true);

                if (canonical.SideboardCards.Count == 0)
                {
                    WriteVarint(stream, 0);
                }
                else
                {
                    WriteVarint(stream, 1);
                    WriteSideboardGroup(
                        stream,
                        canonical.SideboardCards.Where(card => card.Count == 1),
                        false);
                    WriteSideboardGroup(
                        stream,
                        canonical.SideboardCards.Where(card => card.Count == 2),
                        false);
                    WriteSideboardGroup(
                        stream,
                        canonical.SideboardCards.Where(card => card.Count > 2),
                        true);
                }

                return Convert.ToBase64String(stream.ToArray());
            }
        }

        /// <summary>
        /// Decodes a version 1 deckstring into a new canonical deck model.
        /// </summary>
        /// <param name="deckstring">The Base64 deckstring to decode.</param>
        /// <returns>A new canonical deck.</returns>
        /// <exception cref="DeckstringException">The input does not satisfy the shared contract.</exception>
        public static Deck Decode(string deckstring)
        {
            if (string.IsNullOrEmpty(deckstring))
            {
                throw new DeckstringException(
                    DeckstringErrorCodes.InvalidInput,
                    "Deckstring cannot be empty.");
            }
            if (deckstring.Length > MaxBase64Length)
            {
                throw new DeckstringException(
                    DeckstringErrorCodes.LimitExceeded,
                    "Deckstring exceeds the maximum supported size.");
            }
            if (!IsStrictBase64(deckstring))
            {
                throw new DeckstringException(
                    DeckstringErrorCodes.InvalidBase64,
                    "Deckstring is not valid Base64.");
            }

            byte[] bytes;
            try
            {
                bytes = Convert.FromBase64String(deckstring);
            }
            catch (FormatException error)
            {
                throw new DeckstringException(
                    DeckstringErrorCodes.InvalidBase64,
                    "Deckstring is not valid Base64.",
                    error);
            }
            if (bytes.Length > MaxDecodedLength)
            {
                throw new DeckstringException(
                    DeckstringErrorCodes.LimitExceeded,
                    "Deckstring exceeds the maximum supported size.");
            }

            using (var stream = new MemoryStream(bytes, false))
            {
                if (ReadByte(stream) != 0)
                {
                    throw new DeckstringException(
                        DeckstringErrorCodes.InvalidReserved,
                        "Invalid reserved byte.");
                }

                var version = ReadVarint(stream);
                if (version != Version)
                {
                    throw new DeckstringException(
                        DeckstringErrorCodes.UnsupportedVersion,
                        $"Unsupported deckstring version {version}.");
                }

                var formatValue = ReadVarint(stream);
                if (!IsSupportedFormat(formatValue))
                {
                    throw new DeckstringException(
                        DeckstringErrorCodes.UnsupportedFormat,
                        $"Unsupported format {formatValue}.");
                }

                var deck = new Deck { Format = (DeckFormat)formatValue };
                var heroCount = ReadGroupCount(stream);
                if (heroCount == 0)
                {
                    throw new DeckstringException(
                        DeckstringErrorCodes.InvalidCount,
                        "Deckstring must contain at least one hero.");
                }
                for (var index = 0; index < heroCount; index++)
                {
                    deck.Heroes.Add(ReadPositiveVarint(
                        stream,
                        "hero DBF ID",
                        DeckstringErrorCodes.InvalidId));
                }

                for (var group = 1; group <= 3; group++)
                {
                    var count = ReadGroupCount(stream);
                    for (var index = 0; index < count; index++)
                    {
                        var dbfId = ReadPositiveVarint(
                            stream,
                            "card DBF ID",
                            DeckstringErrorCodes.InvalidId);
                        var copies = group == 3
                            ? ReadPositiveVarint(
                                stream,
                                "card count",
                                DeckstringErrorCodes.InvalidCount)
                            : group;
                        deck.Cards.Add(new DeckCard(dbfId, copies));
                    }
                }

                var hasSideboard = stream.Position == stream.Length ? 0 : ReadVarint(stream);
                if (hasSideboard != 0 && hasSideboard != 1)
                {
                    throw new DeckstringException(
                        DeckstringErrorCodes.InvalidSideboard,
                        "Invalid sideboard marker.");
                }

                if (hasSideboard == 1)
                {
                    for (var group = 1; group <= 3; group++)
                    {
                        var count = ReadGroupCount(stream);
                        for (var index = 0; index < count; index++)
                        {
                            var dbfId = ReadPositiveVarint(
                                stream,
                                "sideboard DBF ID",
                                DeckstringErrorCodes.InvalidId);
                            var copies = group == 3
                                ? ReadPositiveVarint(
                                    stream,
                                    "sideboard count",
                                    DeckstringErrorCodes.InvalidCount)
                                : group;
                            var owner = ReadPositiveVarint(
                                stream,
                                "sideboard owner DBF ID",
                                DeckstringErrorCodes.InvalidId);
                            deck.SideboardCards.Add(new SideboardCard(dbfId, copies, owner));
                        }
                    }
                }

                if (stream.Position != stream.Length)
                {
                    throw new DeckstringException(
                        DeckstringErrorCodes.TrailingData,
                        "Deckstring contains trailing data.");
                }

                return Canonicalize(deck);
            }
        }

        /// <summary>
        /// Creates a sorted copy of a deck without legacy zero-count entries.
        /// </summary>
        /// <param name="deck">The deck to canonicalize.</param>
        /// <returns>A new canonical deck; the supplied model is never mutated.</returns>
        /// <exception cref="DeckstringException">The deck cannot be canonicalized safely.</exception>
        public static Deck Canonicalize(Deck deck)
        {
            if (deck == null)
            {
                throw new DeckstringException(
                    DeckstringErrorCodes.InvalidDeck,
                    "Deck cannot be null.");
            }

            var errors = CollectValidationErrors(deck, true);
            if (errors.Count != 0)
            {
                var error = errors[0];
                throw new DeckstringException(error.Code, error.Message);
            }

            var canonical = new Deck { Format = deck.Format };
            foreach (var hero in deck.Heroes.OrderBy(hero => hero))
            {
                canonical.Heroes.Add(hero);
            }

            foreach (var card in deck.Cards.Where(card => card.Count != 0).OrderBy(card => card.DbfId))
            {
                canonical.Cards.Add(new DeckCard(card.DbfId, card.Count));
            }

            foreach (var card in deck.SideboardCards
                .Where(card => card.Count != 0)
                .OrderBy(card => card.OwnerDbfId)
                .ThenBy(card => card.DbfId))
            {
                canonical.SideboardCards.Add(new SideboardCard(
                    card.DbfId,
                    card.Count,
                    card.OwnerDbfId));
            }

            return canonical;
        }

        /// <summary>
        /// Validates a deck without throwing for ordinary invalid user data.
        /// </summary>
        /// <param name="deck">The deck to validate, or <see langword="null"/>.</param>
        /// <returns>All validation failures in deterministic model order.</returns>
        public static ValidationResult Validate(Deck? deck)
        {
            var errors = deck == null
                ? new List<ValidationError>
                {
                    new ValidationError(
                        DeckstringErrorCodes.InvalidDeck,
                        string.Empty,
                        "Deck cannot be null."),
                }
                : CollectValidationErrors(deck, false);
            return new ValidationResult(errors);
        }

        /// <summary>
        /// Projects a deck to the canonical shared JSON transport shape.
        /// </summary>
        /// <param name="deck">The deck to project.</param>
        /// <returns>A new transport model containing numeric tuple arrays.</returns>
        /// <exception cref="DeckstringException">The deck cannot be canonicalized safely.</exception>
        public static DeckTransport ToTransport(Deck deck)
        {
            var canonical = Canonicalize(deck);
            return new DeckTransport
            {
                Format = (int)canonical.Format,
                Heroes = canonical.Heroes.ToArray(),
                Cards = canonical.Cards
                    .Select(card => new[] { card.DbfId, card.Count })
                    .ToArray(),
                SideboardCards = canonical.SideboardCards
                    .Select(card => new[] { card.DbfId, card.Count, card.OwnerDbfId })
                    .ToArray(),
            };
        }

        /// <summary>
        /// Converts the shared JSON transport shape to a canonical typed deck.
        /// </summary>
        /// <param name="transport">The transport model to convert.</param>
        /// <returns>A new canonical typed deck.</returns>
        /// <exception cref="DeckstringException">The transport model violates the shared contract.</exception>
        public static Deck FromTransport(DeckTransport transport)
        {
            if (transport == null)
            {
                throw new DeckstringException(
                    DeckstringErrorCodes.InvalidDeck,
                    "Deck transport cannot be null.");
            }
            if (transport.Heroes == null ||
                transport.Cards == null ||
                transport.SideboardCards == null)
            {
                throw new DeckstringException(
                    DeckstringErrorCodes.InvalidDeck,
                    "Deck transport collections cannot be null.");
            }

            var deck = new Deck { Format = (DeckFormat)transport.Format };
            foreach (var hero in transport.Heroes)
            {
                deck.Heroes.Add(hero);
            }
            for (var index = 0; index < transport.Cards.Length; index++)
            {
                var card = transport.Cards[index];
                if (card == null || card.Length != 2)
                {
                    throw new DeckstringException(
                        DeckstringErrorCodes.InvalidDeck,
                        $"cards[{index}] must be a two-item array.");
                }
                deck.Cards.Add(new DeckCard(card[0], card[1]));
            }
            for (var index = 0; index < transport.SideboardCards.Length; index++)
            {
                var card = transport.SideboardCards[index];
                if (card == null || card.Length != 3)
                {
                    throw new DeckstringException(
                        DeckstringErrorCodes.InvalidDeck,
                        $"sideboardCards[{index}] must be a three-item array.");
                }
                deck.SideboardCards.Add(new SideboardCard(card[0], card[1], card[2]));
            }

            return Canonicalize(deck);
        }

        /// <summary>
        /// Projects a validation result to the shared JSON transport shape.
        /// </summary>
        /// <param name="result">The validation result to project.</param>
        /// <returns>A new validation transport model.</returns>
        public static ValidationResultTransport ToTransport(ValidationResult result)
        {
            if (result == null)
            {
                throw new ArgumentNullException(nameof(result));
            }

            return new ValidationResultTransport
            {
                Valid = result.IsValid,
                Errors = result.Errors
                    .Select(error => new ValidationErrorTransport
                    {
                        Code = error.Code,
                        Path = error.Path,
                        Message = error.Message,
                    })
                    .ToArray(),
            };
        }

        /// <summary>
        /// Parses a full Hearthstone clipboard export.
        /// </summary>
        /// <param name="text">The clipboard text to parse.</param>
        /// <returns>The canonical deck, deckstring, and locale-neutral metadata.</returns>
        /// <exception cref="DeckstringException">The export or its deckstring is invalid.</exception>
        public static DeckExport ParseExport(string text)
        {
            if (string.IsNullOrEmpty(text))
            {
                throw new DeckstringException(
                    DeckstringErrorCodes.InvalidInput,
                    "Deck export cannot be empty.");
            }
            if (text.Length > MaxExportUtf8Length)
            {
                throw new DeckstringException(
                    DeckstringErrorCodes.LimitExceeded,
                    "Deck export exceeds the maximum supported size.");
            }
            if (!TextRules.IsWellFormedUnicode(text))
            {
                throw new DeckstringException(
                    DeckstringErrorCodes.InvalidInput,
                    "Deck export must contain well-formed Unicode.");
            }
            if (Encoding.UTF8.GetByteCount(text) > MaxExportUtf8Length)
            {
                throw new DeckstringException(
                    DeckstringErrorCodes.LimitExceeded,
                    "Deck export exceeds the maximum supported size.");
            }
            if (TextRules.IsExportBlank(text))
            {
                throw new DeckstringException(
                    DeckstringErrorCodes.InvalidInput,
                    "Deck export cannot be empty.");
            }

            var metadata = new DeckExportMetadata();
            string? embeddedDeckstring = null;
            var normalized = text.Replace("\r\n", "\n").Replace('\r', '\n');
            foreach (var sourceLine in normalized.Split('\n'))
            {
                var line = sourceLine;
                if (TextRules.IsExportBlank(line))
                {
                    continue;
                }

                if (line.StartsWith("###", StringComparison.Ordinal))
                {
                    if (embeddedDeckstring != null)
                    {
                        throw new DeckstringException(
                            DeckstringErrorCodes.InvalidInput,
                            "Deck name must appear before the deckstring.");
                    }
                    if (metadata.Name == null)
                    {
                        var name = TextRules.TrimExportWhitespace(line.Substring(3));
                        if (name.Length == 0)
                        {
                            throw new DeckstringException(
                                DeckstringErrorCodes.InvalidInput,
                                "Deck name cannot be empty.");
                        }

                        metadata.Name = name;
                        continue;
                    }
                }

                if (line[0] == '#')
                {
                    var comment = line.Substring(1);
                    if (comment.Length != 0 && comment[0] == ' ')
                    {
                        comment = comment.Substring(1);
                    }
                    metadata.Comments.Add(comment);
                    continue;
                }

                if (embeddedDeckstring != null)
                {
                    throw new DeckstringException(
                        DeckstringErrorCodes.InvalidInput,
                        "Deck export must contain exactly one deckstring.");
                }

                embeddedDeckstring = TextRules.TrimExportWhitespace(line);
            }

            if (embeddedDeckstring == null)
            {
                throw new DeckstringException(
                    DeckstringErrorCodes.InvalidInput,
                    "Deck export does not contain a deckstring.");
            }

            var deck = Decode(embeddedDeckstring);
            return new DeckExport(deck, Encode(deck), metadata);
        }

        /// <summary>
        /// Formats a deck and optional metadata as deterministic LF clipboard text.
        /// </summary>
        /// <param name="deck">The deck to format.</param>
        /// <param name="metadata">Optional deck name and comments.</param>
        /// <param name="cardResolver">
        /// An optional callback that maps a DBF ID to localized display data.
        /// Missing mappings are omitted from the presentation comments.
        /// </param>
        /// <returns>A canonical Hearthstone clipboard export.</returns>
        /// <exception cref="DeckstringException">The deck or metadata is invalid.</exception>
        public static string FormatExport(
            Deck deck,
            DeckExportMetadata? metadata = null,
            Func<int, CardDisplay?>? cardResolver = null)
        {
            var canonical = Canonicalize(deck);
            var lines = new List<string>();

            if (metadata?.Name != null)
            {
                var name = TextRules.TrimExportWhitespace(
                    RequireMetadataLine(metadata.Name, "Deck name"));
                if (name.Length == 0)
                {
                    throw new DeckstringException(
                        DeckstringErrorCodes.InvalidInput,
                        "Deck name cannot be empty.");
                }
                lines.Add("### " + name);
            }

            if (metadata != null)
            {
                foreach (var comment in metadata.Comments)
                {
                    AddComment(lines, RequireMetadataLine(comment, "Deck comment"));
                }
            }

            if (cardResolver != null)
            {
                foreach (var card in canonical.Cards)
                {
                    var display = cardResolver(card.DbfId);
                    if (display != null)
                    {
                        AddComment(
                            lines,
                            string.Format(
                                CultureInfo.InvariantCulture,
                                "{0}x ({1}) {2}",
                                card.Count,
                                display.Cost ?? 0,
                                display.Name));
                    }
                }

                foreach (var card in canonical.SideboardCards)
                {
                    var display = cardResolver(card.DbfId);
                    if (display != null)
                    {
                        AddComment(
                            lines,
                            string.Format(
                                CultureInfo.InvariantCulture,
                                "{0}x ({1}) {2} [sideboard:{3}]",
                                card.Count,
                                display.Cost ?? 0,
                                display.Name,
                                card.OwnerDbfId));
                    }
                }
            }

            if (lines.Count != 0)
            {
                lines.Add("#");
            }
            lines.Add(Encode(canonical));
            return string.Join("\n", lines);
        }

        private static List<ValidationError> CollectValidationErrors(Deck deck, bool allowZeroCounts)
        {
            var errors = new List<ValidationError>();
            if ((long)deck.Heroes.Count + deck.Cards.Count + deck.SideboardCards.Count > MaxItemsPerDeck)
            {
                errors.Add(new ValidationError(
                    DeckstringErrorCodes.LimitExceeded,
                    string.Empty,
                    "Deck contains too many items."));
                return errors;
            }
            if (!IsSupportedFormat((int)deck.Format))
            {
                errors.Add(new ValidationError(
                    DeckstringErrorCodes.UnsupportedFormat,
                    "format",
                    $"Unsupported format {(int)deck.Format}."));
            }

            if (deck.Heroes.Count == 0)
            {
                errors.Add(new ValidationError(
                    DeckstringErrorCodes.InvalidCount,
                    "heroes",
                    "Deck must contain at least one hero."));
            }
            if (deck.Heroes.Count > MaxItemsPerGroup)
            {
                errors.Add(new ValidationError(
                    DeckstringErrorCodes.LimitExceeded,
                    "heroes",
                    "Hero group is too large."));
            }

            var heroes = new HashSet<int>();
            for (var index = 0; index < deck.Heroes.Count; index++)
            {
                var hero = deck.Heroes[index];
                if (hero <= 0)
                {
                    errors.Add(new ValidationError(
                        DeckstringErrorCodes.InvalidId,
                        $"heroes[{index}]",
                        "Hero DBF ID must be positive."));
                }
                if (hero > 0 && !heroes.Add(hero))
                {
                    errors.Add(new ValidationError(
                        DeckstringErrorCodes.InvalidDeck,
                        $"heroes[{index}]",
                        "Hero DBF IDs must be unique."));
                }
            }

            var cards = new HashSet<int>();
            for (var index = 0; index < deck.Cards.Count; index++)
            {
                var card = deck.Cards[index];
                if (card == null)
                {
                    errors.Add(new ValidationError(
                        DeckstringErrorCodes.InvalidDeck,
                        $"cards[{index}]",
                        "Card entry cannot be null."));
                    continue;
                }
                if (card.DbfId <= 0)
                {
                    errors.Add(new ValidationError(
                        DeckstringErrorCodes.InvalidId,
                        $"cards[{index}][0]",
                        "Card DBF ID must be positive."));
                }
                if (card.Count < 0 || !allowZeroCounts && card.Count == 0)
                {
                    errors.Add(new ValidationError(
                        DeckstringErrorCodes.InvalidCount,
                        $"cards[{index}][1]",
                        "Card count must be positive."));
                }
                if (allowZeroCounts && card.Count == 0)
                {
                    continue;
                }
                if (card.DbfId > 0 && !cards.Add(card.DbfId))
                {
                    errors.Add(new ValidationError(
                        DeckstringErrorCodes.InvalidDeck,
                        $"cards[{index}][0]",
                        "Card DBF IDs must be unique."));
                }
            }
            AddCardGroupLimitErrors(deck.Cards, errors, "cards");

            var sideboardCards = new HashSet<long>();
            for (var index = 0; index < deck.SideboardCards.Count; index++)
            {
                var card = deck.SideboardCards[index];
                if (card == null)
                {
                    errors.Add(new ValidationError(
                        DeckstringErrorCodes.InvalidDeck,
                        $"sideboardCards[{index}]",
                        "Sideboard entry cannot be null."));
                    continue;
                }
                if (card.DbfId <= 0)
                {
                    errors.Add(new ValidationError(
                        DeckstringErrorCodes.InvalidId,
                        $"sideboardCards[{index}][0]",
                        "Sideboard DBF ID must be positive."));
                }
                if (card.Count < 0 || !allowZeroCounts && card.Count == 0)
                {
                    errors.Add(new ValidationError(
                        DeckstringErrorCodes.InvalidCount,
                        $"sideboardCards[{index}][1]",
                        "Sideboard count must be positive."));
                }
                if (card.OwnerDbfId <= 0)
                {
                    errors.Add(new ValidationError(
                        DeckstringErrorCodes.InvalidId,
                        $"sideboardCards[{index}][2]",
                        "Sideboard owner DBF ID must be positive."));
                }
                if (allowZeroCounts && card.Count == 0)
                {
                    continue;
                }

                var key = ((long)(uint)card.OwnerDbfId << 32) | (uint)card.DbfId;
                if (card.DbfId > 0 && card.OwnerDbfId > 0 && !sideboardCards.Add(key))
                {
                    errors.Add(new ValidationError(
                        DeckstringErrorCodes.InvalidDeck,
                        $"sideboardCards[{index}]",
                        "Sideboard owner and card DBF ID pairs must be unique."));
                }
            }
            AddSideboardGroupLimitErrors(deck.SideboardCards, errors);

            return errors;
        }

        private static void AddCardGroupLimitErrors(
            IEnumerable<DeckCard> cards,
            List<ValidationError> errors,
            string path)
        {
            if (cards.Count(card => card != null && card.Count == 1) > MaxItemsPerGroup ||
                cards.Count(card => card != null && card.Count == 2) > MaxItemsPerGroup ||
                cards.Count(card => card != null && card.Count > 2) > MaxItemsPerGroup)
            {
                errors.Add(new ValidationError(
                    DeckstringErrorCodes.LimitExceeded,
                    path,
                    "Card item group is too large."));
            }
        }

        private static void AddSideboardGroupLimitErrors(
            IEnumerable<SideboardCard> cards,
            List<ValidationError> errors)
        {
            if (cards.Count(card => card != null && card.Count == 1) > MaxItemsPerGroup ||
                cards.Count(card => card != null && card.Count == 2) > MaxItemsPerGroup ||
                cards.Count(card => card != null && card.Count > 2) > MaxItemsPerGroup)
            {
                errors.Add(new ValidationError(
                    DeckstringErrorCodes.LimitExceeded,
                    "sideboardCards",
                    "Sideboard item group is too large."));
            }
        }

        private static string RequireMetadataLine(string? value, string name)
        {
            if (value == null || TextRules.ContainsLineBreak(value))
            {
                throw new DeckstringException(
                    DeckstringErrorCodes.InvalidInput,
                    $"{name} must be a single line.");
            }

            return value;
        }

        private static void AddComment(List<string> lines, string comment)
        {
            lines.Add(comment.Length == 0 ? "#" : "# " + comment);
        }

        private static bool IsSupportedFormat(int format)
        {
            return format >= (int)DeckFormat.Wild && format <= (int)DeckFormat.Twist;
        }

        private static bool IsStrictBase64(string value)
        {
            if (value.Length % 4 != 0)
            {
                return false;
            }

            var paddingStarted = false;
            var paddingCount = 0;
            foreach (var character in value)
            {
                if (character == '=')
                {
                    paddingStarted = true;
                    paddingCount++;
                    if (paddingCount > 2)
                    {
                        return false;
                    }
                }
                else if (paddingStarted || !(
                    character >= 'A' && character <= 'Z' ||
                    character >= 'a' && character <= 'z' ||
                    character >= '0' && character <= '9' ||
                    character == '+' ||
                    character == '/'))
                {
                    return false;
                }
            }

            return true;
        }

        private static int RequirePositive(int value, string name, string errorCode)
        {
            if (value <= 0)
            {
                throw new DeckstringException(errorCode, $"{name} must be positive.");
            }

            return value;
        }

        private static void WriteCardGroup(
            Stream stream,
            IEnumerable<DeckCard> source,
            bool includeCount)
        {
            var cards = source.ToList();
            WriteVarint(stream, cards.Count);
            foreach (var card in cards)
            {
                WriteVarint(stream, card.DbfId);
                if (includeCount)
                {
                    WriteVarint(stream, card.Count);
                }
            }
        }

        private static void WriteSideboardGroup(
            Stream stream,
            IEnumerable<SideboardCard> source,
            bool includeCount)
        {
            var cards = source.ToList();
            WriteVarint(stream, cards.Count);
            foreach (var card in cards)
            {
                WriteVarint(stream, card.DbfId);
                if (includeCount)
                {
                    WriteVarint(stream, card.Count);
                }
                WriteVarint(stream, card.OwnerDbfId);
            }
        }

        private static int ReadByte(Stream stream)
        {
            var value = stream.ReadByte();
            if (value < 0)
            {
                throw new DeckstringException(
                    DeckstringErrorCodes.UnexpectedEnd,
                    "Unexpected end of deckstring.");
            }

            return value;
        }

        private static int ReadVarint(Stream stream)
        {
            ulong result = 0;
            var shift = 0;
            for (var byteIndex = 0; byteIndex < 5; byteIndex++)
            {
                if (stream.Position >= stream.Length)
                {
                    throw new DeckstringException(
                        byteIndex == 0
                            ? DeckstringErrorCodes.UnexpectedEnd
                            : DeckstringErrorCodes.InvalidVarint,
                        byteIndex == 0
                            ? "Unexpected end of deckstring."
                            : "Deckstring contains a truncated varint.");
                }
                var value = stream.ReadByte();
                result |= ((ulong)value & 0x7fUL) << shift;
                if ((value & 0x80) == 0)
                {
                    if (result > int.MaxValue)
                    {
                        throw new DeckstringException(
                            DeckstringErrorCodes.InvalidVarint,
                            "Deckstring varint is too large.");
                    }

                    return (int)result;
                }

                shift += 7;
            }

            throw new DeckstringException(
                DeckstringErrorCodes.InvalidVarint,
                "Deckstring varint is too large.");
        }

        private static int ReadPositiveVarint(Stream stream, string name, string errorCode)
        {
            return RequirePositive(ReadVarint(stream), name, errorCode);
        }

        private static int ReadGroupCount(Stream stream)
        {
            var count = ReadVarint(stream);
            if (count > MaxItemsPerGroup)
            {
                throw new DeckstringException(
                    DeckstringErrorCodes.LimitExceeded,
                    "Deckstring item group is too large.");
            }

            return count;
        }

        private static void WriteVarint(Stream stream, int value)
        {
            if (value < 0)
            {
                throw new DeckstringException(
                    DeckstringErrorCodes.InvalidVarint,
                    "Cannot encode a negative varint.");
            }

            var remaining = (uint)value;
            do
            {
                var current = (byte)(remaining & 0x7f);
                remaining >>= 7;
                if (remaining != 0)
                {
                    current |= 0x80;
                }
                stream.WriteByte(current);
            }
            while (remaining != 0);
        }
    }
}
