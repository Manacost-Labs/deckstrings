namespace ManacostLabs.Deckstrings
{
    /// <summary>
    /// Represents one validation issue in the shared JSON transport shape.
    /// </summary>
    public sealed class ValidationErrorTransport
    {
        /// <summary>
        /// Gets or sets the stable machine-readable error code.
        /// </summary>
        public string Code { get; set; } = string.Empty;

        /// <summary>
        /// Gets or sets the path of the invalid value.
        /// </summary>
        public string Path { get; set; } = string.Empty;

        /// <summary>
        /// Gets or sets the human-readable description.
        /// </summary>
        public string Message { get; set; } = string.Empty;
    }
}
