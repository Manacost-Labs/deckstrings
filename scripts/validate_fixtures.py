import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource


ROOT = Path(__file__).resolve().parents[1]


def load(path: Path):
	return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
	deck_schema = load(ROOT / "spec" / "deck.schema.json")
	fixtures_schema = load(ROOT / "spec" / "fixtures.schema.json")
	fixtures = load(ROOT / "fixtures" / "deckstrings.json")
	registry = Registry().with_resources(
		[
			(deck_schema["$id"], Resource.from_contents(deck_schema)),
			(fixtures_schema["$id"], Resource.from_contents(fixtures_schema)),
		]
	)
	validator = Draft202012Validator(fixtures_schema, registry=registry)
	errors = sorted(validator.iter_errors(fixtures), key=lambda error: list(error.path))
	if errors:
		for error in errors:
			location = ".".join(str(part) for part in error.path) or "<root>"
			print(f"{location}: {error.message}", file=sys.stderr)
		return 1

	names = [fixture["name"] for fixture in fixtures["valid"]]
	if len(names) != len(set(names)):
		print("Fixture names must be unique.", file=sys.stderr)
		return 1

	print(f"Fixture schema validation passed: {len(names)}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
