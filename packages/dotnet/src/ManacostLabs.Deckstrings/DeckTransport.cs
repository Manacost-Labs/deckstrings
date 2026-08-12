namespace ManacostLabs.Deckstrings
{
    /// <summary>
    /// Represents the exact JSON-compatible shared deck transport shape.
    /// </summary>
    /// <remarks>
    /// Serialize public properties with a camel-case naming policy to match
    /// <c>spec/deck.schema.json</c>.
    /// </remarks>
    public sealed class DeckTransport
    {
        /// <summary>
        /// Gets or sets the numeric Hearthstone deck format.
        /// </summary>
        public int Format { get; set; }

        /// <summary>
        /// Gets or sets the hero DBF IDs.
        /// </summary>
        public int[] Heroes { get; set; } = null!;

        /// <summary>
        /// Gets or sets <c>[dbfId, count]</c> card tuples.
        /// </summary>
        public int[][] Cards { get; set; } = null!;

        /// <summary>
        /// Gets or sets <c>[dbfId, count, ownerDbfId]</c> sideboard tuples.
        /// </summary>
        public int[][] SideboardCards { get; set; } = null!;
    }
}
