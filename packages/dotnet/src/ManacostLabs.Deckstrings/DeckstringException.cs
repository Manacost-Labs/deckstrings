using System;

namespace ManacostLabs.Deckstrings
{
    /// <summary>
    /// Represents a deckstring or canonical deck contract violation.
    /// </summary>
    public sealed class DeckstringException : ArgumentException
    {
        /// <summary>
        /// Initializes a new instance of the <see cref="DeckstringException"/> class.
        /// </summary>
        /// <param name="errorCode">The stable machine-readable error code.</param>
        /// <param name="message">A human-readable description of the error.</param>
        public DeckstringException(string errorCode, string message)
            : base(message)
        {
            ErrorCode = errorCode;
        }

        /// <summary>
        /// Initializes a new instance of the <see cref="DeckstringException"/> class.
        /// </summary>
        /// <param name="errorCode">The stable machine-readable error code.</param>
        /// <param name="message">A human-readable description of the error.</param>
        /// <param name="innerException">The exception that caused this error.</param>
        public DeckstringException(string errorCode, string message, Exception innerException)
            : base(message, innerException)
        {
            ErrorCode = errorCode;
        }

        /// <summary>
        /// Gets the stable machine-readable error code.
        /// </summary>
        public string ErrorCode { get; }
    }
}
