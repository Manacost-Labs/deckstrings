import json
import unittest
from pathlib import Path

from manacost_deckstrings import decode, encode


FIXTURE_PATH = Path(__file__).resolve().parents[3] / "fixtures" / "deckstrings.json"


class CompatibilityTests(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.fixtures = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))["valid"]

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
				self.assertEqual(
					encode(decode(fixture["deckstring"])),
					expected,
				)


if __name__ == "__main__":
	unittest.main()
