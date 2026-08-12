using System.Collections.Generic;

namespace ManacostLabs.Deckstrings
{
    /// <summary>
    /// Represents a Hearthstone deck in the shared canonical data model.
    /// </summary>
    public sealed class Deck
    {
        /// <summary>
        /// Gets or sets the Hearthstone deck format.
        /// </summary>
        public DeckFormat Format { get; set; }

        /// <summary>
        /// Gets the mutable collection of hero DBF IDs.
        /// </summary>
        public IList<int> Heroes { get; } = new List<int>();

        /// <summary>
        /// Gets the mutable collection of cards in the main deck.
        /// </summary>
        public IList<DeckCard> Cards { get; } = new List<DeckCard>();

        /// <summary>
        /// Gets the mutable collection of sideboard cards.
        /// </summary>
        public IList<SideboardCard> SideboardCards { get; } = new List<SideboardCard>();
    }
}
