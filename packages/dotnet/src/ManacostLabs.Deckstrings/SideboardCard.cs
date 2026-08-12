namespace ManacostLabs.Deckstrings
{
    public sealed class SideboardCard
    {
        public SideboardCard(int dbfId, int count, int ownerDbfId)
        {
            DbfId = dbfId;
            Count = count;
            OwnerDbfId = ownerDbfId;
        }

        public int DbfId { get; }

        public int Count { get; }

        public int OwnerDbfId { get; }
    }
}
