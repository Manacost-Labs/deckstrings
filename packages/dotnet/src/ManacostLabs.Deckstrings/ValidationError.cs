namespace ManacostLabs.Deckstrings
{
    /// <summary>
    /// Describes one validation failure without throwing an exception.
    /// </summary>
    public sealed class ValidationError
    {
        /// <summary>
        /// Initializes a new instance of the <see cref="ValidationError"/> class.
        /// </summary>
        /// <param name="code">The stable machine-readable error code.</param>
        /// <param name="path">The path of the invalid value.</param>
        /// <param name="message">A human-readable description of the failure.</param>
        internal ValidationError(string code, string path, string message)
        {
            if (string.IsNullOrWhiteSpace(code))
            {
                throw new System.ArgumentException("Validation code cannot be empty.", nameof(code));
            }
            if (string.IsNullOrWhiteSpace(message))
            {
                throw new System.ArgumentException("Validation message cannot be empty.", nameof(message));
            }

            Code = code;
            Path = path ?? throw new System.ArgumentNullException(nameof(path));
            Message = message;
        }

        /// <summary>
        /// Gets the stable machine-readable error code.
        /// </summary>
        public string Code { get; }

        /// <summary>
        /// Gets the path of the invalid value in the shared deck model.
        /// </summary>
        public string Path { get; }

        /// <summary>
        /// Gets a human-readable description of the validation failure.
        /// </summary>
        public string Message { get; }
    }
}
