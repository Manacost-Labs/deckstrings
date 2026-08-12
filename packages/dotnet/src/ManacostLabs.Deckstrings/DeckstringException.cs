using System;

namespace ManacostLabs.Deckstrings
{
    public sealed class DeckstringException : ArgumentException
    {
        public DeckstringException(string message)
            : base(message)
        {
        }

        public DeckstringException(string message, Exception innerException)
            : base(message, innerException)
        {
        }
    }
}
