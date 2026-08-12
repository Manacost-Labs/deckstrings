using System;

namespace ManacostLabs.Deckstrings
{
    /// <summary>
    /// Represents a validation result in the exact shared JSON transport shape.
    /// </summary>
    /// <remarks>
    /// Serialize public properties with a camel-case naming policy to match
    /// <c>spec/validation-result.schema.json</c>.
    /// </remarks>
    public sealed class ValidationResultTransport
    {
        /// <summary>
        /// Gets or sets a value indicating whether the deck is valid.
        /// </summary>
        public bool Valid { get; set; }

        /// <summary>
        /// Gets or sets the validation issues in deterministic model order.
        /// </summary>
        public ValidationErrorTransport[] Errors { get; set; } =
            Array.Empty<ValidationErrorTransport>();
    }
}
