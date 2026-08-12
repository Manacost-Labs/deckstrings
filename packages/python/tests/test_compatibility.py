import json
import unittest
from pathlib import Path

from manacost_deckstrings import (
    DeckstringError,
    canonicalize,
    decode,
    encode,
    format_export,
    parse_export,
    validate,
)

FIXTURE_ROOT = Path(__file__).resolve().parents[3] / "fixtures"


class CompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        document = json.loads(
            (FIXTURE_ROOT / "deckstrings.json").read_text(encoding="utf-8")
        )
        cls.fixtures = document["valid"]
        cls.invalid_fixtures = document["invalid"]
        cls.api_fixtures = json.loads(
            (FIXTURE_ROOT / "api.json").read_text(encoding="utf-8")
        )
        cls.export_fixtures = json.loads(
            (FIXTURE_ROOT / "exports.json").read_text(encoding="utf-8")
        )

    def test_decodes_shared_fixtures(self):
        for fixture in self.fixtures:
            with self.subTest(fixture=fixture["name"]):
                self.assertEqual(decode(fixture["deckstring"]), fixture["deck"])

    def test_encodes_shared_fixtures(self):
        for fixture in self.fixtures:
            with self.subTest(fixture=fixture["name"]):
                expected = fixture.get("canonicalDeckstring", fixture["deckstring"])
                self.assertEqual(encode(fixture["deck"]), expected)

    def test_round_trips_shared_fixtures(self):
        for fixture in self.fixtures:
            with self.subTest(fixture=fixture["name"]):
                expected = fixture.get("canonicalDeckstring", fixture["deckstring"])
                self.assertEqual(encode(decode(fixture["deckstring"])), expected)

    def test_rejects_shared_invalid_fixtures(self):
        for fixture in self.invalid_fixtures:
            with self.subTest(fixture=fixture["name"]):
                with self.assertRaises(DeckstringError) as context:
                    decode(fixture["deckstring"])
                self.assertEqual(context.exception.code, fixture["errorCode"])

    def test_canonicalization_fixtures(self):
        for fixture in self.api_fixtures["canonicalize"]:
            with self.subTest(fixture=fixture["name"]):
                if "errorCode" in fixture:
                    with self.assertRaises(DeckstringError) as context:
                        canonicalize(fixture["deck"])
                    self.assertEqual(context.exception.code, fixture["errorCode"])
                else:
                    self.assertEqual(
                        canonicalize(fixture["deck"]), fixture["expectedDeck"]
                    )

    def test_validation_fixtures(self):
        for fixture in self.api_fixtures["validate"]:
            with self.subTest(fixture=fixture["name"]):
                result = validate(fixture["deck"])
                projected_errors = [
                    {"code": error["code"], "path": error["path"]}
                    for error in result["errors"]
                ]
                self.assertEqual(result["valid"], fixture["valid"])
                self.assertEqual(projected_errors, fixture["errors"])

    def test_export_fixtures(self):
        for fixture in self.export_fixtures["valid"]:
            with self.subTest(fixture=fixture["name"]):
                parsed = parse_export(fixture["text"])
                self.assertEqual(parsed, fixture["parsed"])
                self.assertEqual(
                    format_export(parsed["deck"], parsed["metadata"]),
                    fixture["formatted"],
                )

    def test_invalid_export_fixtures(self):
        for fixture in self.export_fixtures["invalid"]:
            with self.subTest(fixture=fixture["name"]):
                with self.assertRaises(DeckstringError) as context:
                    parse_export(fixture["text"])
                self.assertEqual(context.exception.code, fixture["errorCode"])

    def test_resolver_fixtures(self):
        for fixture in self.export_fixtures["resolver"]["valid"]:
            with self.subTest(fixture=fixture["name"]):
                cards = fixture["cards"]
                self.assertEqual(
                    format_export(
                        fixture["deck"],
                        fixture["metadata"],
                        lambda dbf_id, cards=cards: cards.get(str(dbf_id)),
                    ),
                    fixture["formatted"],
                )

        for fixture in self.export_fixtures["resolver"]["invalid"]:
            with self.subTest(fixture=fixture["name"]):
                cards = fixture["cards"]
                with self.assertRaises(DeckstringError) as context:
                    format_export(
                        fixture["deck"],
                        {},
                        lambda dbf_id, cards=cards: cards.get(str(dbf_id)),
                    )
                self.assertEqual(context.exception.code, fixture["errorCode"])


if __name__ == "__main__":
    unittest.main()
