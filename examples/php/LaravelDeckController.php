<?php

declare(strict_types=1);

namespace App\Http\Controllers;

use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use ManacostLabs\Deckstrings\Deckstrings;
use ManacostLabs\Deckstrings\DeckstringException;

/**
 * Illustrative Laravel adapter. Register decode() on a POST route and keep the
 * dependency-free codec in the application layer.
 */
final class LaravelDeckController extends Controller
{
    public function decode(Request $request): JsonResponse
    {
        /** @var array{deckstring: string} $input */
        $input = $request->validate([
            'deckstring' => ['required', 'string', 'max:1398104'],
        ]);

        try {
            $deck = Deckstrings::decode($input['deckstring']);

            return response()->json([
                'deck' => $deck,
                'deckstring' => Deckstrings::encode($deck),
            ]);
        } catch (DeckstringException $error) {
            return response()->json([
                'error' => [
                    'code' => $error->getErrorCode(),
                    'message' => 'The deckstring is invalid.',
                ],
            ], 422);
        }
    }
}
