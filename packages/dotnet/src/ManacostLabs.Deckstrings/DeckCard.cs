namespace ManacostLabs.Deckstrings
{
    /// <summary>
    /// Represents one card entry in a deck.
    /// </summary>
    public sealed class DeckCard
    {
        /// <summary>
        /// Initializes a new instance of the <see cref="DeckCard"/> class.
        /// </summary>
        /// <param name="dbfId">The card DBF ID.</param>
        /// <param name="count">The number of copies.</param>
        public DeckCard(int dbfId, int count)
        {
            DbfId = dbfId;
            Count = count;
        }

        /// <summary>
        /// Gets the card DBF ID.
        /// </summary>
        public int DbfId { get; }

        /// <summary>
        /// Gets the number of copies.
        /// </summary>
        public int Count { get; }
    }
}
