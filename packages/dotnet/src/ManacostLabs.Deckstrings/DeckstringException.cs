using System;

namespace ManacostLabs.Deckstrings
{
    public sealed class DeckstringException : ArgumentException
    {
        public DeckstringException(string errorCode, string message)
            : base(message)
        {
            ErrorCode = errorCode;
        }

        public DeckstringException(string errorCode, string message, Exception innerException)
            : base(message, innerException)
        {
            ErrorCode = errorCode;
        }

        public string ErrorCode { get; }
    }
}
