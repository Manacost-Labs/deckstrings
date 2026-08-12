<?php

declare(strict_types=1);

require_once __DIR__ . '/../src/DeckstringException.php';
require_once __DIR__ . '/../src/Deckstrings.php';

use ManacostLabs\Deckstrings\Deckstrings;
use ManacostLabs\Deckstrings\DeckstringException;

/** @return array<string, mixed> */
function fixtureDocument(string $name): array
{
    $path = __DIR__ . '/../../../fixtures/' . $name;
    $document = json_decode((string) file_get_contents($path), true, flags: JSON_THROW_ON_ERROR);
    if (!is_array($document)) {
        throw new RuntimeException(sprintf('%s did not contain a JSON object.', $name));
    }

    return $document;
}

$document = fixtureDocument('deckstrings.json');
$apiDocument = fixtureDocument('api.json');
$exportDocument = fixtureDocument('exports.json');
$checked = 0;

foreach ($document['valid'] as $fixture) {
    $canonicalDeckstring = $fixture['canonicalDeckstring'] ?? $fixture['deckstring'];
    $decoded = Deckstrings::decode($fixture['deckstring']);
    if ($decoded != $fixture['deck']) {
        throw new RuntimeException(sprintf('%s did not decode to the canonical deck.', $fixture['name']));
    }

    $encoded = Deckstrings::encode($fixture['deck']);
    if ($encoded !== $canonicalDeckstring) {
        throw new RuntimeException(sprintf('%s did not encode to the golden deckstring.', $fixture['name']));
    }

    if (Deckstrings::encode($decoded) !== $canonicalDeckstring) {
        throw new RuntimeException(sprintf('%s did not round-trip byte-for-byte.', $fixture['name']));
    }

    $checked++;
}

foreach ($document['invalid'] as $fixture) {
    try {
        Deckstrings::decode($fixture['deckstring']);
        throw new RuntimeException(sprintf('%s did not throw.', $fixture['name']));
    } catch (DeckstringException $error) {
        if ($error->getErrorCode() !== $fixture['errorCode']) {
            throw new RuntimeException(sprintf(
                '%s returned %s instead of %s.',
                $fixture['name'],
                $error->getErrorCode(),
                $fixture['errorCode']
            ));
        }
    }

    $checked++;
}

foreach ($apiDocument['canonicalize'] as $fixture) {
    if (isset($fixture['errorCode'])) {
        try {
            Deckstrings::canonicalize($fixture['deck']);
            throw new RuntimeException(sprintf('%s did not throw.', $fixture['name']));
        } catch (DeckstringException $error) {
            if ($error->getErrorCode() !== $fixture['errorCode']) {
                throw new RuntimeException(sprintf('%s returned the wrong error.', $fixture['name']));
            }
        }
    } elseif (Deckstrings::canonicalize($fixture['deck']) != $fixture['expectedDeck']) {
        throw new RuntimeException(sprintf('%s did not canonicalize correctly.', $fixture['name']));
    }
    $checked++;
}

foreach ($apiDocument['validate'] as $fixture) {
    $result = Deckstrings::validate($fixture['deck']);
    $projectedErrors = array_map(
        static fn (array $error): array => ['code' => $error['code'], 'path' => $error['path']],
        $result['errors']
    );
    if ($result['valid'] !== $fixture['valid'] || $projectedErrors != $fixture['errors']) {
        throw new RuntimeException(sprintf('%s did not validate correctly.', $fixture['name']));
    }
    $checked++;
}

foreach ($exportDocument['valid'] as $fixture) {
    $parsed = Deckstrings::parseExport($fixture['text']);
    if ($parsed != $fixture['parsed']) {
        throw new RuntimeException(sprintf('%s did not parse correctly.', $fixture['name']));
    }
    if (Deckstrings::formatExport($parsed['deck'], $parsed['metadata']) !== $fixture['formatted']) {
        throw new RuntimeException(sprintf('%s did not format correctly.', $fixture['name']));
    }
    $checked++;
}

foreach ($exportDocument['invalid'] as $fixture) {
    try {
        Deckstrings::parseExport($fixture['text']);
        throw new RuntimeException(sprintf('%s did not throw.', $fixture['name']));
    } catch (DeckstringException $error) {
        if ($error->getErrorCode() !== $fixture['errorCode']) {
            throw new RuntimeException(sprintf('%s returned the wrong error.', $fixture['name']));
        }
    }
    $checked++;
}

foreach ($exportDocument['resolver']['valid'] as $fixture) {
    $cards = $fixture['cards'];
    $formatted = Deckstrings::formatExport(
        $fixture['deck'],
        $fixture['metadata'],
        static fn (int $dbfId): ?array => $cards[(string) $dbfId] ?? null
    );
    if ($formatted !== $fixture['formatted']) {
        throw new RuntimeException(sprintf('%s did not format correctly.', $fixture['name']));
    }
    $checked++;
}

foreach ($exportDocument['resolver']['invalid'] as $fixture) {
    $cards = $fixture['cards'];
    try {
        Deckstrings::formatExport(
            $fixture['deck'],
            [],
            static fn (int $dbfId): ?array => $cards[(string) $dbfId] ?? null
        );
        throw new RuntimeException(sprintf('%s did not throw.', $fixture['name']));
    } catch (DeckstringException $error) {
        if ($error->getErrorCode() !== $fixture['errorCode']) {
            throw new RuntimeException(sprintf('%s returned the wrong error.', $fixture['name']));
        }
    }
    $checked++;
}

fwrite(STDOUT, sprintf("PHP compatibility fixtures passed: %d\n", $checked));
