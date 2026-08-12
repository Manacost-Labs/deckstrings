using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;

namespace ManacostLabs.Deckstrings
{
    public static class Deckstrings
    {
        private const int Version = 1;
        private const int MaxItemsPerGroup = 10000;
        private const int MaxBase64Length = 1398104;

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

        private static Deck Canonicalize(Deck deck)
        {
            if (!IsSupportedFormat((int)deck.Format))
            {
                throw new DeckstringException(
                    DeckstringErrorCodes.UnsupportedFormat,
                    $"Unsupported format {(int)deck.Format}.");
            }

            var canonical = new Deck { Format = deck.Format };
            foreach (var hero in deck.Heroes.OrderBy(hero => hero))
            {
                canonical.Heroes.Add(RequirePositive(
                    hero,
                    "hero DBF ID",
                    DeckstringErrorCodes.InvalidId));
            }

            foreach (var card in deck.Cards.Where(card => card.Count != 0).OrderBy(card => card.DbfId))
            {
                canonical.Cards.Add(new DeckCard(
                    RequirePositive(card.DbfId, "card DBF ID", DeckstringErrorCodes.InvalidId),
                    RequirePositive(card.Count, "card count", DeckstringErrorCodes.InvalidCount)));
            }

            foreach (var card in deck.SideboardCards
                .Where(card => card.Count != 0)
                .OrderBy(card => card.OwnerDbfId)
                .ThenBy(card => card.DbfId))
            {
                canonical.SideboardCards.Add(new SideboardCard(
                    RequirePositive(card.DbfId, "sideboard DBF ID", DeckstringErrorCodes.InvalidId),
                    RequirePositive(card.Count, "sideboard count", DeckstringErrorCodes.InvalidCount),
                    RequirePositive(
                        card.OwnerDbfId,
                        "sideboard owner DBF ID",
                        DeckstringErrorCodes.InvalidId)));
            }

            return canonical;
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
