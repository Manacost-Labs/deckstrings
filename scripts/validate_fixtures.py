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
	export_schema = load(ROOT / "spec" / "export.schema.json")
	export_fixtures_schema = load(ROOT / "spec" / "export-fixtures.schema.json")
	api_fixtures_schema = load(ROOT / "spec" / "api-fixtures.schema.json")
	validation_result_schema = load(ROOT / "spec" / "validation-result.schema.json")
	fixtures = load(ROOT / "fixtures" / "deckstrings.json")
	export_fixtures = load(ROOT / "fixtures" / "exports.json")
	api_fixtures = load(ROOT / "fixtures" / "api.json")
	registry = Registry().with_resources(
		[
			(deck_schema["$id"], Resource.from_contents(deck_schema)),
			(fixtures_schema["$id"], Resource.from_contents(fixtures_schema)),
			(export_schema["$id"], Resource.from_contents(export_schema)),
			(export_fixtures_schema["$id"], Resource.from_contents(export_fixtures_schema)),
			(api_fixtures_schema["$id"], Resource.from_contents(api_fixtures_schema)),
			(validation_result_schema["$id"], Resource.from_contents(validation_result_schema)),
		]
	)
	validator = Draft202012Validator(fixtures_schema, registry=registry)
	errors = sorted(validator.iter_errors(fixtures), key=lambda error: list(error.path))
	if errors:
		for error in errors:
			location = ".".join(str(part) for part in error.path) or "<root>"
			print(f"{location}: {error.message}", file=sys.stderr)
		return 1

	export_validator = Draft202012Validator(export_fixtures_schema, registry=registry)
	export_errors = sorted(
		export_validator.iter_errors(export_fixtures),
		key=lambda error: list(error.path),
	)
	if export_errors:
		for error in export_errors:
			location = ".".join(str(part) for part in error.path) or "<root>"
			print(f"exports.{location}: {error.message}", file=sys.stderr)
		return 1

	api_validator = Draft202012Validator(api_fixtures_schema, registry=registry)
	api_errors = sorted(api_validator.iter_errors(api_fixtures), key=lambda error: list(error.path))
	if api_errors:
		for error in api_errors:
			location = ".".join(str(part) for part in error.path) or "<root>"
			print(f"api.{location}: {error.message}", file=sys.stderr)
		return 1

	names = [fixture["name"] for fixture in fixtures["valid"]]
	if len(names) != len(set(names)):
		print("Fixture names must be unique.", file=sys.stderr)
		return 1
	export_names = [fixture["name"] for fixture in export_fixtures["valid"]]
	resolver_names = [
		fixture["name"]
		for group in (
			export_fixtures["resolver"]["valid"],
			export_fixtures["resolver"]["invalid"],
		)
		for fixture in group
	]
	export_names.extend(resolver_names)
	if len(export_names) != len(set(export_names)):
		print("Export fixture names must be unique.", file=sys.stderr)
		return 1
	api_names = [
		fixture["name"]
		for group in (api_fixtures["canonicalize"], api_fixtures["validate"])
		for fixture in group
	]
	if len(api_names) != len(set(api_names)):
		print("API fixture names must be unique.", file=sys.stderr)
		return 1

	print(
		"Fixture schema validation passed: "
		f"{len(names)} deckstrings, {len(export_names) - len(resolver_names)} exports, "
		f"{len(resolver_names)} resolver cases, {len(api_names)} API cases"
	)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
