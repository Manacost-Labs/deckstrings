using System.Collections.Generic;

namespace ManacostLabs.Deckstrings
{
    public sealed class Deck
    {
        public DeckFormat Format { get; set; }

        public IList<int> Heroes { get; } = new List<int>();

        public IList<DeckCard> Cards { get; } = new List<DeckCard>();

        public IList<SideboardCard> SideboardCards { get; } = new List<SideboardCard>();
    }
}
