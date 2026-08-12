<?php

declare(strict_types=1);

namespace ManacostLabs\Deckstrings;

final class Deckstrings
{
    private const VERSION = 1;
    private const SUPPORTED_FORMATS = [1, 2, 3, 4];
    private const MAX_ITEMS_PER_GROUP = 10000;
    private const MAX_ITEMS_PER_DECK = 30000;
    private const MAX_TOP_LEVEL_PROPERTIES = 16;
    private const MAX_DECODED_LENGTH = 1048576;
    private const MAX_BASE64_LENGTH = 1398104;
    private const MAX_EXPORT_UTF8_LENGTH = 1500000;
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
        $deck = self::canonicalize($deck);
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
        if (strlen($binary) > self::MAX_DECODED_LENGTH) {
            throw new DeckstringException(
                DeckstringException::LIMIT_EXCEEDED,
                'Deckstring exceeds the maximum supported size.'
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

        return self::canonicalize([
            'format' => $format,
            'heroes' => $heroes,
            'cards' => $cards,
            'sideboardCards' => $sideboardCards,
        ]);
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
    public static function canonicalize(array $deck): array
    {
        $errors = self::validateDeck($deck, true);
        if ($errors !== []) {
            $error = $errors[0];
            $location = $error['path'] === '' ? '' : sprintf(' at %s', $error['path']);
            throw new DeckstringException(
                $error['code'],
                sprintf('%s%s.', $error['message'], $location)
            );
        }

        $format = $deck['format'] ?? null;
        $rawHeroes = $deck['heroes'] ?? null;
        $rawCards = $deck['cards'] ?? null;
        $rawSideboardCards = array_key_exists('sideboardCards', $deck)
            ? $deck['sideboardCards']
            : [];
        if (!is_int($format) || !is_array($rawHeroes) || !is_array($rawCards) || !is_array($rawSideboardCards)) {
            throw new \LogicException('Validated deck has an unexpected internal shape.');
        }

        $heroes = [];
        foreach ($rawHeroes as $hero) {
            if (!is_int($hero)) {
                throw new \LogicException('Validated hero has an unexpected internal type.');
            }
            $heroes[] = $hero;
        }
        sort($heroes, SORT_NUMERIC);

        /** @var list<array{int, int}> $cards */
        $cards = [];
        foreach ($rawCards as $card) {
            if (
                !is_array($card)
                || !isset($card[0], $card[1])
                || !is_int($card[0])
                || !is_int($card[1])
            ) {
                throw new \LogicException('Validated card has an unexpected internal shape.');
            }
            if ($card[1] !== 0) {
                $cards[] = [$card[0], $card[1]];
            }
        }
        usort($cards, static fn (array $left, array $right): int => $left[0] <=> $right[0]);

        /** @var list<array{int, int, int}> $sideboardCards */
        $sideboardCards = [];
        foreach ($rawSideboardCards as $card) {
            if (
                !is_array($card)
                || !isset($card[0], $card[1], $card[2])
                || !is_int($card[0])
                || !is_int($card[1])
                || !is_int($card[2])
            ) {
                throw new \LogicException('Validated sideboard card has an unexpected internal shape.');
            }
            if ($card[1] !== 0) {
                $sideboardCards[] = [$card[0], $card[1], $card[2]];
            }
        }
        usort(
            $sideboardCards,
            static fn (array $left, array $right): int =>
                ($left[2] <=> $right[2]) ?: ($left[0] <=> $right[0])
        );

        return [
            'format' => $format,
            'heroes' => $heroes,
            'cards' => $cards,
            'sideboardCards' => $sideboardCards,
        ];
    }

    /**
     * @return array{
     *   valid: bool,
     *   errors: list<array{code: string, path: string, message: string}>
     * }
     */
    public static function validate(mixed $deck): array
    {
        $errors = self::validateDeck($deck, false);

        return ['valid' => $errors === [], 'errors' => $errors];
    }

    /**
     * @return array{
     *   deck: array{
     *     format: int,
     *     heroes: list<int>,
     *     cards: list<array{int, int}>,
     *     sideboardCards: list<array{int, int, int}>
     *   },
     *   deckstring: string,
     *   metadata: array{name?: string, comments: list<string>}
     * }
     */
    public static function parseExport(string $text): array
    {
        if ($text === '') {
            throw new DeckstringException(
                DeckstringException::INVALID_INPUT,
                'Export must be a non-empty string.'
            );
        }
        if (strlen($text) > self::MAX_EXPORT_UTF8_LENGTH) {
            throw new DeckstringException(
                DeckstringException::LIMIT_EXCEEDED,
                'Export exceeds the maximum supported size.'
            );
        }
        if (preg_match('//u', $text) !== 1) {
            throw new DeckstringException(
                DeckstringException::INVALID_INPUT,
                'Export must contain well-formed Unicode.'
            );
        }

        $name = null;
        $comments = [];
        $deckstrings = [];
        $lines = preg_split('/\r\n|\n|\r/', $text);
        if ($lines === false) {
            throw new DeckstringException(
                DeckstringException::INVALID_INPUT,
                'Export could not be split into lines.'
            );
        }

        foreach ($lines as $line) {
            if (self::trimExportWhitespace($line) === '') {
                continue;
            }
            if (str_starts_with($line, '###')) {
                if ($deckstrings !== []) {
                    throw new DeckstringException(
                        DeckstringException::INVALID_INPUT,
                        'Deck name must appear before the deckstring.'
                    );
                }
                if ($name === null) {
                    $candidate = self::trimExportWhitespace(substr($line, 3));
                    if ($candidate === '') {
                        throw new DeckstringException(
                            DeckstringException::INVALID_INPUT,
                            'Deck name cannot be empty.'
                        );
                    }
                    $name = $candidate;
                } else {
                    $comments[] = self::stripExportComment($line);
                }
                continue;
            }
            if (str_starts_with($line, '#')) {
                $comments[] = self::stripExportComment($line);
                continue;
            }
            $deckstrings[] = self::trimExportWhitespace($line);
        }

        if (count($deckstrings) !== 1) {
            throw new DeckstringException(
                DeckstringException::INVALID_INPUT,
                'Export must contain exactly one deckstring.'
            );
        }

        $deck = self::decode($deckstrings[0]);
        $metadata = ['comments' => $comments];
        if ($name !== null) {
            $metadata['name'] = $name;
        }

        return [
            'deck' => $deck,
            'deckstring' => self::encode($deck),
            'metadata' => $metadata,
        ];
    }

    /**
     * @param array<string, mixed> $deck
     * @param array<string, mixed> $metadata
     * @param null|callable(int): mixed $resolveCard
     */
    public static function formatExport(
        array $deck,
        array $metadata = [],
        ?callable $resolveCard = null
    ): string {
        $canonical = self::canonicalize($deck);
        $lines = [];

        if (array_key_exists('name', $metadata)) {
            $name = self::trimExportWhitespace(
                self::requireExportText($metadata['name'], 'deck name', false)
            );
            if ($name === '') {
                throw new DeckstringException(
                    DeckstringException::INVALID_INPUT,
                    'Deck name cannot be empty.'
                );
            }
            $lines[] = sprintf('### %s', $name);
        }

        $comments = array_key_exists('comments', $metadata)
            ? $metadata['comments']
            : [];
        if (!is_array($comments) || !array_is_list($comments)) {
            throw new DeckstringException(
                DeckstringException::INVALID_INPUT,
                'Export comments must be an array.'
            );
        }
        foreach ($comments as $index => $commentValue) {
            $comment = self::requireExportText(
                $commentValue,
                sprintf('comments[%d]', $index),
                true
            );
            $lines[] = $comment === '' ? '#' : sprintf('# %s', $comment);
        }

        if ($resolveCard !== null) {
            foreach ($canonical['cards'] as [$dbfId, $count]) {
                $line = self::resolveCardLine($resolveCard, $dbfId, $count);
                if ($line !== null) {
                    $lines[] = sprintf('# %s', $line);
                }
            }
            foreach ($canonical['sideboardCards'] as [$dbfId, $count, $owner]) {
                $line = self::resolveCardLine($resolveCard, $dbfId, $count, $owner);
                if ($line !== null) {
                    $lines[] = sprintf('# %s', $line);
                }
            }
        }

        $deckstring = self::encode($canonical);
        if ($lines === []) {
            return $deckstring;
        }
        $lines[] = '#';
        $lines[] = $deckstring;

        return implode("\n", $lines);
    }

    /**
     * @return list<array{code: string, path: string, message: string}>
     */
    private static function validateDeck(mixed $deck, bool $allowZeroCounts): array
    {
        if (!is_array($deck) || array_is_list($deck)) {
            return [[
                'code' => DeckstringException::INVALID_DECK,
                'path' => '',
                'message' => 'deck must be an object',
            ]];
        }

        if (count($deck) > self::MAX_TOP_LEVEL_PROPERTIES) {
            return [self::validationIssue(
                DeckstringException::LIMIT_EXCEEDED,
                '',
                'deck contains too many properties'
            )];
        }

        $totalItems = 0;
        foreach (['heroes', 'cards', 'sideboardCards'] as $group) {
            if (isset($deck[$group]) && is_array($deck[$group])) {
                $totalItems += count($deck[$group]);
            }
        }
        if ($totalItems > self::MAX_ITEMS_PER_DECK) {
            return [self::validationIssue(
                DeckstringException::LIMIT_EXCEEDED,
                '',
                'deck contains too many items'
            )];
        }

        $errors = [];
        foreach (array_keys($deck) as $key) {
            if (!is_string($key) || !in_array($key, ['format', 'heroes', 'cards', 'sideboardCards'], true)) {
                $errors[] = self::validationIssue(
                    DeckstringException::INVALID_DECK,
                    (string) $key,
                    'deck contains an unknown property'
                );
            }
        }

        $format = $deck['format'] ?? null;
        if (!is_int($format) || !in_array($format, self::SUPPORTED_FORMATS, true)) {
            $errors[] = self::validationIssue(
                DeckstringException::UNSUPPORTED_FORMAT,
                'format',
                'format is not supported'
            );
        }

        $heroes = $deck['heroes'] ?? null;
        if (!is_array($heroes) || !array_is_list($heroes)) {
            $errors[] = self::validationIssue(
                DeckstringException::INVALID_DECK,
                'heroes',
                'heroes must be an array'
            );
        } else {
            if ($heroes === []) {
                $errors[] = self::validationIssue(
                    DeckstringException::INVALID_COUNT,
                    'heroes',
                    'at least one hero is required'
                );
            }
            if (count($heroes) > self::MAX_ITEMS_PER_GROUP) {
                $errors[] = self::validationIssue(
                    DeckstringException::LIMIT_EXCEEDED,
                    'heroes',
                    'hero group is too large'
                );
            }
            $seenHeroes = [];
            foreach ($heroes as $index => $hero) {
                $path = sprintf('heroes[%d]', $index);
                if (!is_int($hero) || $hero <= 0 || $hero > self::MAX_VARINT) {
                    $errors[] = self::validationIssue(
                        DeckstringException::INVALID_ID,
                        $path,
                        'hero DBF ID must be a positive integer'
                    );
                } elseif (isset($seenHeroes[$hero])) {
                    $errors[] = self::validationIssue(
                        DeckstringException::INVALID_DECK,
                        $path,
                        'hero DBF ID is duplicated'
                    );
                } else {
                    $seenHeroes[$hero] = true;
                }
            }
        }

        $cards = $deck['cards'] ?? null;
        if (!is_array($cards) || !array_is_list($cards)) {
            $errors[] = self::validationIssue(
                DeckstringException::INVALID_DECK,
                'cards',
                'cards must be an array'
            );
        } else {
            $seenCards = [];
            $groupCounts = [0, 0, 0];
            foreach ($cards as $index => $card) {
                $path = sprintf('cards[%d]', $index);
                if (!is_array($card) || !array_is_list($card) || count($card) !== 2) {
                    $errors[] = self::validationIssue(
                        DeckstringException::INVALID_DECK,
                        $path,
                        'card must contain two integers'
                    );
                    continue;
                }

                [$dbfId, $count] = $card;
                $validId = is_int($dbfId) && $dbfId > 0 && $dbfId <= self::MAX_VARINT;
                if (!$validId) {
                    $errors[] = self::validationIssue(
                        DeckstringException::INVALID_ID,
                        sprintf('%s[0]', $path),
                        'card DBF ID must be a positive integer'
                    );
                }
                $validCount = is_int($count) && $count >= 0 && $count <= self::MAX_VARINT;
                if (!$validCount || ($count === 0 && !$allowZeroCounts)) {
                    $errors[] = self::validationIssue(
                        DeckstringException::INVALID_COUNT,
                        sprintf('%s[1]', $path),
                        'card count must be a positive integer'
                    );
                }
                if ($validCount && $count === 0 && $allowZeroCounts) {
                    continue;
                }
                if ($validId) {
                    if (isset($seenCards[$dbfId])) {
                        $errors[] = self::validationIssue(
                            DeckstringException::INVALID_DECK,
                            sprintf('%s[0]', $path),
                            'card DBF ID is duplicated'
                        );
                    } else {
                        $seenCards[$dbfId] = true;
                    }
                }
                if ($validCount && $count > 0) {
                    $group = $count === 1 ? 0 : ($count === 2 ? 1 : 2);
                    $groupCounts[$group]++;
                }
            }
            if (max($groupCounts) > self::MAX_ITEMS_PER_GROUP) {
                $errors[] = self::validationIssue(
                    DeckstringException::LIMIT_EXCEEDED,
                    'cards',
                    'card group is too large'
                );
            }
        }

        $sideboardCards = array_key_exists('sideboardCards', $deck)
            ? $deck['sideboardCards']
            : [];
        if (!is_array($sideboardCards) || !array_is_list($sideboardCards)) {
            $errors[] = self::validationIssue(
                DeckstringException::INVALID_DECK,
                'sideboardCards',
                'sideboardCards must be an array'
            );
        } else {
            $seenSideboards = [];
            $groupCounts = [0, 0, 0];
            foreach ($sideboardCards as $index => $card) {
                $path = sprintf('sideboardCards[%d]', $index);
                if (!is_array($card) || !array_is_list($card) || count($card) !== 3) {
                    $errors[] = self::validationIssue(
                        DeckstringException::INVALID_DECK,
                        $path,
                        'sideboard card must contain three integers'
                    );
                    continue;
                }

                [$dbfId, $count, $owner] = $card;
                $validId = is_int($dbfId) && $dbfId > 0 && $dbfId <= self::MAX_VARINT;
                $validOwner = is_int($owner) && $owner > 0 && $owner <= self::MAX_VARINT;
                if (!$validId) {
                    $errors[] = self::validationIssue(
                        DeckstringException::INVALID_ID,
                        sprintf('%s[0]', $path),
                        'sideboard DBF ID must be a positive integer'
                    );
                }
                $validCount = is_int($count) && $count >= 0 && $count <= self::MAX_VARINT;
                if (!$validCount || ($count === 0 && !$allowZeroCounts)) {
                    $errors[] = self::validationIssue(
                        DeckstringException::INVALID_COUNT,
                        sprintf('%s[1]', $path),
                        'sideboard count must be a positive integer'
                    );
                }
                if (!$validOwner) {
                    $errors[] = self::validationIssue(
                        DeckstringException::INVALID_ID,
                        sprintf('%s[2]', $path),
                        'sideboard owner DBF ID must be a positive integer'
                    );
                }
                if ($validCount && $count === 0 && $allowZeroCounts) {
                    continue;
                }
                if ($validId && $validOwner) {
                    $key = sprintf('%d:%d', $owner, $dbfId);
                    if (isset($seenSideboards[$key])) {
                        $errors[] = self::validationIssue(
                            DeckstringException::INVALID_DECK,
                            $path,
                            'sideboard owner and card pair is duplicated'
                        );
                    } else {
                        $seenSideboards[$key] = true;
                    }
                }
                if ($validCount && $count > 0) {
                    $group = $count === 1 ? 0 : ($count === 2 ? 1 : 2);
                    $groupCounts[$group]++;
                }
            }
            if (max($groupCounts) > self::MAX_ITEMS_PER_GROUP) {
                $errors[] = self::validationIssue(
                    DeckstringException::LIMIT_EXCEEDED,
                    'sideboardCards',
                    'sideboard group is too large'
                );
            }
        }

        return $errors;
    }

    /** @return array{code: string, path: string, message: string} */
    private static function validationIssue(string $code, string $path, string $message): array
    {
        return ['code' => $code, 'path' => $path, 'message' => $message];
    }

    private static function stripExportComment(string $line): string
    {
        $comment = substr($line, 1);

        return str_starts_with($comment, ' ') ? substr($comment, 1) : $comment;
    }

    private static function requireExportText(mixed $value, string $name, bool $allowEmpty): string
    {
        if (!is_string($value) || (!$allowEmpty && $value === '')) {
            throw new DeckstringException(
                DeckstringException::INVALID_INPUT,
                sprintf('%s must be a string.', $name)
            );
        }
        if (str_contains($value, "\n") || str_contains($value, "\r")) {
            throw new DeckstringException(
                DeckstringException::INVALID_INPUT,
                sprintf('%s must contain one line.', $name)
            );
        }

        return $value;
    }

    private static function trimExportWhitespace(string $value): string
    {
        $trimmed = preg_replace(
            '/^[\x{0009}-\x{000D}\x{0020}\x{0085}\x{00A0}\x{1680}\x{2000}-\x{200A}\x{2028}\x{2029}\x{202F}\x{205F}\x{3000}]+|[\x{0009}-\x{000D}\x{0020}\x{0085}\x{00A0}\x{1680}\x{2000}-\x{200A}\x{2028}\x{2029}\x{202F}\x{205F}\x{3000}]+$/u',
            '',
            $value
        );

        return $trimmed ?? $value;
    }

    /**
     * @param callable(int): mixed $resolveCard
     */
    private static function resolveCardLine(
        callable $resolveCard,
        int $dbfId,
        int $count,
        ?int $owner = null
    ): ?string {
        $resolved = $resolveCard($dbfId);
        if ($resolved === null) {
            return null;
        }
        if (!is_array($resolved)) {
            throw new DeckstringException(
                DeckstringException::INVALID_INPUT,
                'Card resolver must return an array or null.'
            );
        }
        $name = self::requireExportText($resolved['name'] ?? null, 'resolved card name', false);
        $cost = $resolved['cost'] ?? 0;
        if (self::trimExportWhitespace($name) === '') {
            throw new DeckstringException(
                DeckstringException::INVALID_INPUT,
                'Resolved card name cannot be blank.'
            );
        }
        if (!is_int($cost) || $cost < 0 || $cost > self::MAX_VARINT) {
            throw new DeckstringException(
                DeckstringException::INVALID_INPUT,
                'Resolved card cost must be a non-negative integer.'
            );
        }
        $suffix = $owner === null ? '' : sprintf(' [sideboard:%d]', $owner);

        return sprintf('%dx (%d) %s%s', $count, $cost, $name, $suffix);
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
