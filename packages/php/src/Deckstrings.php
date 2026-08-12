<?php

declare(strict_types=1);

namespace ManacostLabs\Deckstrings;

final class Deckstrings
{
    private const VERSION = 1;
    private const SUPPORTED_FORMATS = [1, 2, 3, 4];
    private const MAX_ITEMS_PER_GROUP = 10000;
    private const MAX_BASE64_LENGTH = 1398104;
    private const MAX_VARINT = 2147483647;

    /**
     * @param array{
     *   format: int,
     *   heroes: list<int>,
     *   cards: list<array{int, int}>,
     *   sideboardCards?: list<array{int, int, int}>
     * } $deck
     */
    public static function encode(array $deck): string
    {
        $deck = self::normalizeDeck($deck);
        $binary = "\x00";
        self::writeVarint($binary, self::VERSION);
        self::writeVarint($binary, $deck['format']);
        self::writeVarint($binary, count($deck['heroes']));

        foreach ($deck['heroes'] as $hero) {
            self::writeVarint($binary, $hero);
        }

        foreach (self::partitionByCount($deck['cards']) as $index => $group) {
            self::writeVarint($binary, count($group));
            foreach ($group as $card) {
                self::writeVarint($binary, $card[0]);
                if ($index === 2) {
                    self::writeVarint($binary, $card[1]);
                }
            }
        }

        if ($deck['sideboardCards'] === []) {
            self::writeVarint($binary, 0);

            return base64_encode($binary);
        }

        self::writeVarint($binary, 1);
        foreach (self::partitionByCount($deck['sideboardCards']) as $index => $group) {
            self::writeVarint($binary, count($group));
            foreach ($group as $card) {
                self::writeVarint($binary, $card[0]);
                if ($index === 2) {
                    self::writeVarint($binary, $card[1]);
                }
                self::writeVarint($binary, $card[2]);
            }
        }

        return base64_encode($binary);
    }

    /**
     * @return array{
     *   format: int,
     *   heroes: list<int>,
     *   cards: list<array{int, int}>,
     *   sideboardCards: list<array{int, int, int}>
     * }
     */
    public static function decode(string $deckstring): array
    {
        if ($deckstring === '') {
            throw new DeckstringException(
                DeckstringException::INVALID_INPUT,
                'Deckstring cannot be empty.'
            );
        }
        if (strlen($deckstring) > self::MAX_BASE64_LENGTH) {
            throw new DeckstringException(
                DeckstringException::LIMIT_EXCEEDED,
                'Deckstring exceeds the maximum supported size.'
            );
        }
        if (strlen($deckstring) % 4 !== 0 || preg_match('/^[A-Za-z0-9+\/]*={0,2}$/D', $deckstring) !== 1) {
            throw new DeckstringException(
                DeckstringException::INVALID_BASE64,
                'Deckstring is not valid Base64.'
            );
        }

        $binary = base64_decode($deckstring, true);
        if ($binary === false) {
            throw new DeckstringException(
                DeckstringException::INVALID_BASE64,
                'Deckstring is not valid Base64.'
            );
        }

        $offset = 0;
        if (self::readByte($binary, $offset) !== 0) {
            throw new DeckstringException(
                DeckstringException::INVALID_RESERVED,
                'Invalid reserved byte.'
            );
        }

        $version = self::readVarint($binary, $offset);
        if ($version !== self::VERSION) {
            throw new DeckstringException(
                DeckstringException::UNSUPPORTED_VERSION,
                sprintf('Unsupported deckstring version %d.', $version)
            );
        }

        $format = self::readVarint($binary, $offset);
        if (!in_array($format, self::SUPPORTED_FORMATS, true)) {
            throw new DeckstringException(
                DeckstringException::UNSUPPORTED_FORMAT,
                sprintf('Unsupported format %d.', $format)
            );
        }

        $heroes = [];
        $heroCount = self::readGroupCount($binary, $offset);
        if ($heroCount === 0) {
            throw new DeckstringException(
                DeckstringException::INVALID_COUNT,
                'Deckstring must contain at least one hero.'
            );
        }
        for ($index = 0; $index < $heroCount; $index++) {
            $heroes[] = self::readPositiveVarint(
                $binary,
                $offset,
                'hero DBF ID',
                DeckstringException::INVALID_ID
            );
        }
        sort($heroes, SORT_NUMERIC);

        $cards = [];
        for ($group = 1; $group <= 3; $group++) {
            $count = self::readGroupCount($binary, $offset);
            for ($index = 0; $index < $count; $index++) {
                $dbfId = self::readPositiveVarint(
                    $binary,
                    $offset,
                    'card DBF ID',
                    DeckstringException::INVALID_ID
                );
                $copies = $group === 3
                    ? self::readPositiveVarint(
                        $binary,
                        $offset,
                        'card count',
                        DeckstringException::INVALID_COUNT
                    )
                    : $group;
                $cards[] = [$dbfId, $copies];
            }
        }
        usort($cards, static fn (array $left, array $right): int => $left[0] <=> $right[0]);

        $sideboardCards = [];
        $hasSideboard = $offset < strlen($binary)
            ? self::readVarint($binary, $offset)
            : 0;
        if ($hasSideboard !== 0 && $hasSideboard !== 1) {
            throw new DeckstringException(
                DeckstringException::INVALID_SIDEBOARD,
                'Invalid sideboard marker.'
            );
        }

        if ($hasSideboard === 1) {
            for ($group = 1; $group <= 3; $group++) {
                $count = self::readGroupCount($binary, $offset);
                for ($index = 0; $index < $count; $index++) {
                    $dbfId = self::readPositiveVarint(
                        $binary,
                        $offset,
                        'sideboard DBF ID',
                        DeckstringException::INVALID_ID
                    );
                    $copies = $group === 3
                        ? self::readPositiveVarint(
                            $binary,
                            $offset,
                            'sideboard count',
                            DeckstringException::INVALID_COUNT
                        )
                        : $group;
                    $owner = self::readPositiveVarint(
                        $binary,
                        $offset,
                        'sideboard owner DBF ID',
                        DeckstringException::INVALID_ID
                    );
                    $sideboardCards[] = [$dbfId, $copies, $owner];
                }
            }
            usort(
                $sideboardCards,
                static fn (array $left, array $right): int =>
                    ($left[2] <=> $right[2]) ?: ($left[0] <=> $right[0])
            );
        }

        if ($offset !== strlen($binary)) {
            throw new DeckstringException(
                DeckstringException::TRAILING_DATA,
                'Deckstring contains trailing data.'
            );
        }

        return [
            'format' => $format,
            'heroes' => $heroes,
            'cards' => $cards,
            'sideboardCards' => $sideboardCards,
        ];
    }

    /**
     * @param array<string, mixed> $deck
     * @return array{
     *   format: int,
     *   heroes: list<int>,
     *   cards: list<array{int, int}>,
     *   sideboardCards: list<array{int, int, int}>
     * }
     */
    private static function normalizeDeck(array $deck): array
    {
        if (!isset($deck['format']) || !is_int($deck['format'])) {
            throw new DeckstringException(
                DeckstringException::INVALID_DECK,
                'Deck format must be an integer.'
            );
        }
        if (!in_array($deck['format'], self::SUPPORTED_FORMATS, true)) {
            throw new DeckstringException(
                DeckstringException::UNSUPPORTED_FORMAT,
                sprintf('Unsupported format %d.', $deck['format'])
            );
        }
        if (!isset($deck['heroes']) || !is_array($deck['heroes'])) {
            throw new DeckstringException(DeckstringException::INVALID_DECK, 'Deck heroes must be an array.');
        }
        if (!isset($deck['cards']) || !is_array($deck['cards'])) {
            throw new DeckstringException(DeckstringException::INVALID_DECK, 'Deck cards must be an array.');
        }
        if (isset($deck['sideboardCards']) && !is_array($deck['sideboardCards'])) {
            throw new DeckstringException(
                DeckstringException::INVALID_DECK,
                'Deck sideboardCards must be an array.'
            );
        }

        $heroes = [];
        foreach ($deck['heroes'] as $hero) {
            $heroes[] = self::requirePositiveInteger($hero, 'hero DBF ID');
        }
        sort($heroes, SORT_NUMERIC);

        $cards = [];
        foreach ($deck['cards'] as $card) {
            $normalized = self::normalizeTuple($card, 2, 'card');
            if ($normalized[1] !== 0) {
                $cards[] = $normalized;
            }
        }
        usort($cards, static fn (array $left, array $right): int => $left[0] <=> $right[0]);

        $sideboardCards = [];
        foreach ($deck['sideboardCards'] ?? [] as $card) {
            $normalized = self::normalizeTuple($card, 3, 'sideboard card');
            if ($normalized[1] !== 0) {
                $sideboardCards[] = $normalized;
            }
        }
        usort(
            $sideboardCards,
            static fn (array $left, array $right): int =>
                ($left[2] <=> $right[2]) ?: ($left[0] <=> $right[0])
        );

        return [
            'format' => $deck['format'],
            'heroes' => $heroes,
            'cards' => $cards,
            'sideboardCards' => $sideboardCards,
        ];
    }

    /** @return list<int> */
    private static function normalizeTuple(mixed $value, int $length, string $name): array
    {
        if (!is_array($value) || count($value) !== $length || !array_is_list($value)) {
            throw new DeckstringException(
                DeckstringException::INVALID_DECK,
                sprintf('%s must contain exactly %d integers.', $name, $length)
            );
        }

        $tuple = [];
        foreach ($value as $index => $item) {
            if ($index === 1) {
                if (!is_int($item) || $item < 0) {
                    throw new DeckstringException(
                        DeckstringException::INVALID_COUNT,
                        sprintf('%s count must be a non-negative integer.', $name)
                    );
                }
                $tuple[] = $item;
            } else {
                $tuple[] = self::requirePositiveInteger($item, sprintf('%s DBF ID', $name));
            }
        }

        return $tuple;
    }

    private static function requirePositiveInteger(mixed $value, string $name): int
    {
        if (!is_int($value) || $value <= 0) {
            throw new DeckstringException(
                DeckstringException::INVALID_ID,
                sprintf('%s must be a positive integer.', $name)
            );
        }

        return $value;
    }

    /**
     * @param list<array<int, int>> $cards
     * @return array{list<array<int, int>>, list<array<int, int>>, list<array<int, int>>}
     */
    private static function partitionByCount(array $cards): array
    {
        $groups = [[], [], []];
        foreach ($cards as $card) {
            $index = $card[1] === 1 ? 0 : ($card[1] === 2 ? 1 : 2);
            $groups[$index][] = $card;
        }

        return $groups;
    }

    private static function readByte(string $binary, int &$offset): int
    {
        if ($offset >= strlen($binary)) {
            throw new DeckstringException(
                DeckstringException::UNEXPECTED_END,
                'Unexpected end of deckstring.'
            );
        }

        return ord($binary[$offset++]);
    }

    private static function readVarint(string $binary, int &$offset): int
    {
        $result = 0;
        $shift = 0;
        for ($byteIndex = 0; $byteIndex < 5; $byteIndex++) {
            if ($offset >= strlen($binary)) {
                throw new DeckstringException(
                    $byteIndex === 0
                        ? DeckstringException::UNEXPECTED_END
                        : DeckstringException::INVALID_VARINT,
                    $byteIndex === 0
                        ? 'Unexpected end of deckstring.'
                        : 'Deckstring contains a truncated varint.'
                );
            }
            $byte = ord($binary[$offset++]);
            $result |= ($byte & 0x7f) << $shift;
            if (($byte & 0x80) === 0) {
                if ($result > self::MAX_VARINT) {
                    throw new DeckstringException(
                        DeckstringException::INVALID_VARINT,
                        'Deckstring varint is too large.'
                    );
                }
                return $result;
            }
            $shift += 7;
        }

        throw new DeckstringException(
            DeckstringException::INVALID_VARINT,
            'Deckstring varint is too large.'
        );
    }

    private static function readPositiveVarint(
        string $binary,
        int &$offset,
        string $name,
        string $errorCode
    ): int
    {
        $value = self::readVarint($binary, $offset);
        if ($value <= 0) {
            throw new DeckstringException($errorCode, sprintf('%s must be positive.', $name));
        }

        return $value;
    }

    private static function readGroupCount(string $binary, int &$offset): int
    {
        $count = self::readVarint($binary, $offset);
        if ($count > self::MAX_ITEMS_PER_GROUP) {
            throw new DeckstringException(
                DeckstringException::LIMIT_EXCEEDED,
                'Deckstring item group is too large.'
            );
        }

        return $count;
    }

    private static function writeVarint(string &$binary, int $value): void
    {
        if ($value < 0) {
            throw new DeckstringException(
                DeckstringException::INVALID_VARINT,
                'Cannot encode a negative varint.'
            );
        }

        do {
            $byte = $value & 0x7f;
            $value >>= 7;
            if ($value !== 0) {
                $byte |= 0x80;
            }
            $binary .= chr($byte);
        } while ($value !== 0);
    }
}
