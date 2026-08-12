from copy import deepcopy

import pytest

from manacost_deckstrings import (
    DeckstringError,
    canonicalize,
    decode,
    format_export,
    parse_export,
    validate,
)


def test_parse_export_rejects_oversized_utf8_text():
    with pytest.raises(DeckstringError) as context:
        parse_export("🔥" * 375_001)

    assert context.value.code == "limit_exceeded"


def test_parse_export_rejects_malformed_unicode_with_stable_code():
    with pytest.raises(DeckstringError) as context:
        parse_export("\ud800")

    assert context.value.code == "invalid_input"


def test_canonicalize_does_not_mutate_input():
    deck = {
        "format": 1,
        "heroes": [10, 2],
        "cards": [[4, 1], [3, 2]],
        "sideboardCards": [[7, 1, 10], [6, 2, 2]],
    }
    original = deepcopy(deck)

    canonicalize(deck)

    assert deck == original


@pytest.mark.parametrize(
    ("deck", "code"),
    [
        ({"format": 1, "heroes": [], "cards": []}, "invalid_count"),
        ({"format": 1, "heroes": [2_147_483_648], "cards": []}, "invalid_id"),
        (
            {"format": 1, "heroes": [7], "cards": [[1, 2_147_483_648]]},
            "invalid_count",
        ),
    ],
)
def test_canonicalize_rejects_invalid_input(deck, code):
    with pytest.raises(DeckstringError, match=".+") as context:
        canonicalize(deck)

    assert context.value.code == code


def test_validate_accepts_non_mapping_without_raising():
    result = validate(None)

    assert result["valid"] is False
    assert result["errors"][0]["code"] == "invalid_deck"


def test_validate_bounds_excessive_top_level_properties():
    result = validate({f"field{index}": index for index in range(17)})

    assert result["valid"] is False
    assert result["errors"] == [
        {
            "code": "limit_exceeded",
            "path": "",
            "message": "deck contains too many properties",
        }
    ]


def test_decode_rejects_duplicate_card_ids():
    with pytest.raises(DeckstringError) as context:
        decode("AAEBAQcCAQEAAAA=")

    assert context.value.code == "invalid_deck"


def test_format_export_uses_card_resolver_for_main_and_sideboard_cards():
    deck = {
        "format": 1,
        "heroes": [7],
        "cards": [[1, 2]],
        "sideboardCards": [[5, 1, 10]],
    }
    cards = {
        1: {"name": "Main Card", "cost": 3},
        5: {"name": "Sideboard Card"},
    }

    text = format_export(deck, {"comments": ["Format: Wild"]}, cards.get)

    assert "# 2x (3) Main Card" in text
    assert "# 1x (0) Sideboard Card [sideboard:10]" in text
    assert text.splitlines()[-2] == "#"


@pytest.mark.parametrize(
    "card",
    [
        {"name": "   ", "cost": 0},
        {"name": "Card", "cost": 2_147_483_648},
    ],
)
def test_format_export_rejects_invalid_card_resolver_data(card):
    deck = {"format": 1, "heroes": [7], "cards": [[1, 1]]}

    with pytest.raises(DeckstringError) as context:
        format_export(deck, resolve_card=lambda _dbf_id: card)

    assert context.value.code == "invalid_input"


@pytest.mark.parametrize(
    "metadata",
    [
        {"comments": ["two\nlines"]},
        {"name": "", "comments": []},
    ],
)
def test_format_export_rejects_ambiguous_metadata(metadata):
    deck = {"format": 1, "heroes": [7], "cards": []}

    with pytest.raises(DeckstringError) as context:
        format_export(deck, metadata)

    assert context.value.code == "invalid_input"


def test_format_export_preserves_hashes_in_comment_content():
    deck = {"format": 1, "heroes": [7], "cards": []}

    text = format_export(deck, {"comments": ["## Alternate Heading"]})

    assert text.splitlines()[0] == "# ## Alternate Heading"
