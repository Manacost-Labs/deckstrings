namespace ManacostLabs.Deckstrings
{
    /// <summary>
    /// Supplies optional locale-specific display data when formatting an export.
    /// </summary>
    public sealed class CardDisplay
    {
        /// <summary>
        /// Initializes a new instance of the <see cref="CardDisplay"/> class.
        /// </summary>
        /// <param name="name">The localized card name.</param>
        /// <param name="cost">The optional mana cost. Missing costs are formatted as zero.</param>
        public CardDisplay(string name, int? cost = null)
        {
            if (name == null || TextRules.IsExportBlank(name))
            {
                throw new DeckstringException(
                    DeckstringErrorCodes.InvalidInput,
                    "Card display name cannot be empty.");
            }
            if (TextRules.ContainsLineBreak(name))
            {
                throw new DeckstringException(
                    DeckstringErrorCodes.InvalidInput,
                    "Card display name must be a single line.");
            }
            if (cost < 0)
            {
                throw new DeckstringException(
                    DeckstringErrorCodes.InvalidInput,
                    "Card display cost cannot be negative.");
            }

            Name = name;
            Cost = cost;
        }

        /// <summary>
        /// Gets the localized card name.
        /// </summary>
        public string Name { get; }

        /// <summary>
        /// Gets the optional mana cost.
        /// </summary>
        public int? Cost { get; }
    }
}
