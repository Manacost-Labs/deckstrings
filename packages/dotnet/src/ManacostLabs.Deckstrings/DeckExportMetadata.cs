using System.Collections.Generic;

namespace ManacostLabs.Deckstrings
{
    /// <summary>
    /// Represents locale-neutral metadata preserved outside a binary deckstring.
    /// </summary>
    public sealed class DeckExportMetadata
    {
        /// <summary>
        /// Gets or sets the optional deck name.
        /// </summary>
        public string? Name { get; set; }

        /// <summary>
        /// Gets the mutable list of comments without the leading hash marker.
        /// </summary>
        public IList<string> Comments { get; } = new List<string>();
    }
}
