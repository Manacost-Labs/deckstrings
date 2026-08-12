<?php

declare(strict_types=1);

namespace ManacostLabs\Deckstrings\Tests;

use ManacostLabs\Deckstrings\Deckstrings;
use ManacostLabs\Deckstrings\DeckstringException;
use PHPUnit\Framework\Attributes\DataProvider;
use PHPUnit\Framework\TestCase;

final class DeckstringsTest extends TestCase
{
    public function testCanonicalizeDoesNotMutateInput(): void
    {
        $deck = [
            'format' => 1,
            'heroes' => [10, 2],
            'cards' => [[4, 1], [3, 2]],
            'sideboardCards' => [[7, 1, 10], [6, 2, 2]],
        ];
        $original = $deck;

        Deckstrings::canonicalize($deck);

        self::assertSame($original, $deck);
    }

    /** @return iterable<string, array{array<string, mixed>, string}> */
    public static function invalidDeckProvider(): iterable
    {
        yield 'empty heroes' => [
            ['format' => 1, 'heroes' => [], 'cards' => []],
            DeckstringException::INVALID_COUNT,
        ];
        yield 'oversized hero ID' => [
            ['format' => 1, 'heroes' => [2147483648], 'cards' => []],
            DeckstringException::INVALID_ID,
        ];
        yield 'oversized count' => [
            ['format' => 1, 'heroes' => [7], 'cards' => [[1, 2147483648]]],
            DeckstringException::INVALID_COUNT,
        ];
    }

    /** @param array<string, mixed> $deck */
    #[DataProvider('invalidDeckProvider')]
    public function testCanonicalizeRejectsInvalidInput(array $deck, string $code): void
    {
        try {
            Deckstrings::canonicalize($deck);
            self::fail('Expected DeckstringException.');
        } catch (DeckstringException $error) {
            self::assertSame($code, $error->getErrorCode());
        }
    }

    public function testValidateAcceptsNonArrayWithoutThrowing(): void
    {
        $result = Deckstrings::validate(null);

        self::assertFalse($result['valid']);
        self::assertSame(DeckstringException::INVALID_DECK, $result['errors'][0]['code']);
    }

    public function testValidateBoundsExcessiveTopLevelProperties(): void
    {
        $deck = [];
        for ($index = 0; $index < 17; $index++) {
            $deck[sprintf('field%d', $index)] = $index;
        }

        $result = Deckstrings::validate($deck);

        self::assertFalse($result['valid']);
        self::assertSame(DeckstringException::LIMIT_EXCEEDED, $result['errors'][0]['code']);
        self::assertCount(1, $result['errors']);
    }

    public function testDecodeRejectsDuplicateCardIds(): void
    {
        try {
            Deckstrings::decode('AAEBAQcCAQEAAAA=');
            self::fail('Expected DeckstringException.');
        } catch (DeckstringException $error) {
            self::assertSame(DeckstringException::INVALID_DECK, $error->getErrorCode());
        }
    }

    public function testParseExportRejectsOversizedUtf8Text(): void
    {
        try {
            Deckstrings::parseExport(str_repeat('a', 1500001));
            self::fail('Expected DeckstringException.');
        } catch (DeckstringException $error) {
            self::assertSame(DeckstringException::LIMIT_EXCEEDED, $error->getErrorCode());
        }
    }

    public function testParseExportRejectsMalformedUnicodeWithStableCode(): void
    {
        try {
            Deckstrings::parseExport("\xED\xA0\x80");
            self::fail('Expected DeckstringException.');
        } catch (DeckstringException $error) {
            self::assertSame(DeckstringException::INVALID_INPUT, $error->getErrorCode());
        }
    }

    public function testFormatExportUsesCardResolver(): void
    {
        $deck = [
            'format' => 1,
            'heroes' => [7],
            'cards' => [[1, 2]],
            'sideboardCards' => [[5, 1, 10]],
        ];
        $cards = [
            1 => ['name' => 'Main Card', 'cost' => 3],
            5 => ['name' => 'Sideboard Card'],
        ];

        $text = Deckstrings::formatExport(
            $deck,
            ['comments' => ['Format: Wild']],
            static fn (int $dbfId): ?array => $cards[$dbfId] ?? null
        );

        self::assertStringContainsString('# 2x (3) Main Card', $text);
        self::assertStringContainsString('# 1x (0) Sideboard Card [sideboard:10]', $text);
        self::assertSame('#', explode("\n", $text)[count(explode("\n", $text)) - 2]);
    }

    public function testFormatExportPreservesHashesInCommentContent(): void
    {
        $text = Deckstrings::formatExport(
            ['format' => 1, 'heroes' => [7], 'cards' => []],
            ['comments' => ['## Alternate Heading']]
        );

        self::assertSame('# ## Alternate Heading', explode("\n", $text)[0]);
    }

    public function testFormatExportRejectsNullComments(): void
    {
        try {
            Deckstrings::formatExport(
                ['format' => 1, 'heroes' => [7], 'cards' => []],
                ['comments' => null]
            );
            self::fail('Expected DeckstringException.');
        } catch (DeckstringException $error) {
            self::assertSame(DeckstringException::INVALID_INPUT, $error->getErrorCode());
        }
    }
}
