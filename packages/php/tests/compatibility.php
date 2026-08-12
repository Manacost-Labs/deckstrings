<?php

declare(strict_types=1);

require_once __DIR__ . '/../src/DeckstringException.php';
require_once __DIR__ . '/../src/Deckstrings.php';

use ManacostLabs\Deckstrings\Deckstrings;

$fixturePath = __DIR__ . '/../../../fixtures/deckstrings.json';
$document = json_decode((string) file_get_contents($fixturePath), true, flags: JSON_THROW_ON_ERROR);
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

fwrite(STDOUT, sprintf("PHP compatibility fixtures passed: %d\n", $checked));
