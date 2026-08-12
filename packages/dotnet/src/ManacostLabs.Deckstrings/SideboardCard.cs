namespace ManacostLabs.Deckstrings
{
    /// <summary>
    /// Represents one card entry in a sideboard.
    /// </summary>
    public sealed class SideboardCard
    {
        /// <summary>
        /// Initializes a new instance of the <see cref="SideboardCard"/> class.
        /// </summary>
        /// <param name="dbfId">The sideboard card DBF ID.</param>
        /// <param name="count">The number of copies.</param>
        /// <param name="ownerDbfId">The DBF ID of the card that owns the sideboard.</param>
        public SideboardCard(int dbfId, int count, int ownerDbfId)
        {
            DbfId = dbfId;
            Count = count;
            OwnerDbfId = ownerDbfId;
        }

        /// <summary>
        /// Gets the sideboard card DBF ID.
        /// </summary>
        public int DbfId { get; }

        /// <summary>
        /// Gets the number of copies.
        /// </summary>
        public int Count { get; }

        /// <summary>
        /// Gets the DBF ID of the card that owns the sideboard.
        /// </summary>
        public int OwnerDbfId { get; }
    }
}
