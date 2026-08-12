using System;

namespace ManacostLabs.Deckstrings
{
    /// <summary>
    /// Represents a parsed Hearthstone clipboard export.
    /// </summary>
    public sealed class DeckExport
    {
        /// <summary>
        /// Initializes a new instance of the <see cref="DeckExport"/> class.
        /// </summary>
        /// <param name="deck">The canonical deck model.</param>
        /// <param name="deckstring">The canonical deckstring.</param>
        /// <param name="metadata">The locale-neutral export metadata.</param>
        internal DeckExport(Deck deck, string deckstring, DeckExportMetadata metadata)
        {
            Deck = deck ?? throw new ArgumentNullException(nameof(deck));
            if (string.IsNullOrWhiteSpace(deckstring))
            {
                throw new ArgumentException("Deckstring cannot be empty.", nameof(deckstring));
            }

            Deckstring = deckstring;
            Metadata = metadata ?? throw new ArgumentNullException(nameof(metadata));
        }

        /// <summary>
        /// Gets the canonical deck model.
        /// </summary>
        public Deck Deck { get; }

        /// <summary>
        /// Gets the canonical embedded deckstring.
        /// </summary>
        public string Deckstring { get; }

        /// <summary>
        /// Gets the parsed export metadata.
        /// </summary>
        public DeckExportMetadata Metadata { get; }
    }
}
