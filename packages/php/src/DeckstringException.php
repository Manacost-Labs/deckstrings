<?php

declare(strict_types=1);

namespace ManacostLabs\Deckstrings;

final class DeckstringException extends \InvalidArgumentException
{
    public const INVALID_INPUT = 'invalid_input';
    public const INVALID_BASE64 = 'invalid_base64';
    public const UNEXPECTED_END = 'unexpected_end';
    public const INVALID_RESERVED = 'invalid_reserved';
    public const UNSUPPORTED_VERSION = 'unsupported_version';
    public const UNSUPPORTED_FORMAT = 'unsupported_format';
    public const INVALID_VARINT = 'invalid_varint';
    public const INVALID_ID = 'invalid_id';
    public const INVALID_COUNT = 'invalid_count';
    public const INVALID_SIDEBOARD = 'invalid_sideboard';
    public const TRAILING_DATA = 'trailing_data';
    public const LIMIT_EXCEEDED = 'limit_exceeded';
    public const INVALID_DECK = 'invalid_deck';

    public function __construct(
        private readonly string $errorCode,
        string $message,
        ?\Throwable $previous = null
    ) {
        parent::__construct($message, 0, $previous);
    }

    public function getErrorCode(): string
    {
        return $this->errorCode;
    }
}
