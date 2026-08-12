namespace ManacostLabs.Deckstrings
{
    /// <summary>
    /// Defines stable machine-readable deckstring error codes.
    /// </summary>
    public static class DeckstringErrorCodes
    {
        /// <summary>The input is missing or structurally invalid.</summary>
        public const string InvalidInput = "invalid_input";

        /// <summary>The input is not strict Base64.</summary>
        public const string InvalidBase64 = "invalid_base64";

        /// <summary>The binary input ended before the expected value.</summary>
        public const string UnexpectedEnd = "unexpected_end";

        /// <summary>The reserved byte has an unsupported value.</summary>
        public const string InvalidReserved = "invalid_reserved";

        /// <summary>The deckstring version is unsupported.</summary>
        public const string UnsupportedVersion = "unsupported_version";

        /// <summary>The deck format is unsupported.</summary>
        public const string UnsupportedFormat = "unsupported_format";

        /// <summary>A variable-length integer is malformed.</summary>
        public const string InvalidVarint = "invalid_varint";

        /// <summary>A DBF ID is invalid.</summary>
        public const string InvalidId = "invalid_id";

        /// <summary>A collection or card count is invalid.</summary>
        public const string InvalidCount = "invalid_count";

        /// <summary>The sideboard data is invalid.</summary>
        public const string InvalidSideboard = "invalid_sideboard";

        /// <summary>Unexpected bytes follow the decoded deck.</summary>
        public const string TrailingData = "trailing_data";

        /// <summary>A defensive input limit was exceeded.</summary>
        public const string LimitExceeded = "limit_exceeded";

        /// <summary>The in-memory deck model is invalid.</summary>
        public const string InvalidDeck = "invalid_deck";
    }
}
