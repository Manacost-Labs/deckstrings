using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;

namespace ManacostLabs.Deckstrings
{
    /// <summary>
    /// Contains all validation failures found in a deck.
    /// </summary>
    public sealed class ValidationResult
    {
        /// <summary>
        /// Initializes a new instance of the <see cref="ValidationResult"/> class.
        /// </summary>
        /// <param name="errors">The validation failures.</param>
        internal ValidationResult(IEnumerable<ValidationError> errors)
        {
            Errors = new ReadOnlyCollection<ValidationError>(
                errors == null
                    ? throw new ArgumentNullException(nameof(errors))
                    : new List<ValidationError>(errors));
        }

        /// <summary>
        /// Gets a value indicating whether the deck is valid.
        /// </summary>
        public bool IsValid => Errors.Count == 0;

        /// <summary>
        /// Gets the validation failures in deterministic model order.
        /// </summary>
        public IReadOnlyList<ValidationError> Errors { get; }
    }
}
