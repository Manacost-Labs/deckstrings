<?php

declare(strict_types=1);

use ManacostLabs\Deckstrings\Deckstrings;
use ManacostLabs\Deckstrings\DeckstringException;

$autoload = getenv('COMPOSER_AUTOLOAD');
if ($autoload === false || $autoload === '') {
    $autoload = __DIR__ . '/vendor/autoload.php';
}
if (!is_file($autoload)) {
    throw new RuntimeException(
        'Install the Composer package or set COMPOSER_AUTOLOAD to vendor/autoload.php.'
    );
}
require $autoload;

/** @param mixed $actual */
function expectSame(mixed $expected, mixed $actual, string $message): void
{
    if ($actual !== $expected) {
        throw new RuntimeException($message);
    }
}

$input = [
    'format' => 1,
    'heroes' => [7],
    'cards' => [[4, 1], [1, 2]],
    'sideboardCards' => [[5, 1, 90749]],
];

$canonical = Deckstrings::canonicalize($input);
expectSame([[1, 2], [4, 1]], $canonical['cards'], 'Cards were not canonicalized.');
expectSame(true, Deckstrings::validate($canonical)['valid'], 'Deck should be valid.');

$deckstring = Deckstrings::encode($canonical);
expectSame($canonical, Deckstrings::decode($deckstring), 'Round trip changed the deck.');

$parsed = Deckstrings::parseExport(
    "### API example\n# Format: Wild\n#\n{$deckstring}"
);
expectSame('API example', $parsed['metadata']['name'] ?? null, 'Name was not parsed.');
expectSame($deckstring, $parsed['deckstring'], 'Deckstring was not canonical.');

$cards = [
    1 => ['name' => 'First Card', 'cost' => 1],
    4 => ['name' => 'Fourth Card', 'cost' => 4],
    5 => ['name' => 'Sideboard Card'],
];
$formatted = Deckstrings::formatExport(
    $parsed['deck'],
    ['name' => 'API example', 'comments' => ['Format: Wild']],
    static fn (int $dbfId): ?array => $cards[$dbfId] ?? null
);

if (!str_contains($formatted, '# 2x (1) First Card')) {
    throw new RuntimeException('Main-deck resolver output is missing.');
}
if (!str_contains($formatted, '# 1x (0) Sideboard Card [sideboard:90749]')) {
    throw new RuntimeException('Sideboard resolver output is missing.');
}

try {
    Deckstrings::decode('not-base64!');
    throw new RuntimeException('Invalid input should throw.');
} catch (DeckstringException $error) {
    expectSame('invalid_base64', $error->getErrorCode(), 'Unexpected error code.');
}

fwrite(STDOUT, $formatted . PHP_EOL);
