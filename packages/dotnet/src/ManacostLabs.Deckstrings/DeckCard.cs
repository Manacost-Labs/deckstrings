namespace ManacostLabs.Deckstrings
{
    public sealed class DeckCard
    {
        public DeckCard(int dbfId, int count)
        {
            DbfId = dbfId;
            Count = count;
        }

        public int DbfId { get; }

        public int Count { get; }
    }
}
