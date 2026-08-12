#!/usr/bin/env python3
"""Ensure every published package uses the same semantic version."""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
COMPOSER_NAME = "manacost-labs/hearthstone-deckstrings"
COMPOSER_AUTOLOAD = {"ManacostLabs\\Deckstrings\\": "packages/php/src/"}


def read_versions() -> dict[str, str]:
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    with (ROOT / "packages/python/pyproject.toml").open("rb") as handle:
        python_project = tomllib.load(handle)
    dotnet = ET.parse(
        ROOT
        / "packages/dotnet/src/ManacostLabs.Deckstrings/ManacostLabs.Deckstrings.csproj"
    )
    dotnet_version = dotnet.findtext(".//Version")
    if dotnet_version is None:
        raise ValueError("NuGet <Version> is missing from the project file")
    consumer = ET.parse(
        ROOT
        / "packages/dotnet/tests/ManacostLabs.Deckstrings.Consumer/ManacostLabs.Deckstrings.Consumer.csproj"
    )
    consumer_version = consumer.findtext(".//DeckstringsPackageVersion")
    if consumer_version is None:
        raise ValueError("NuGet consumer <DeckstringsPackageVersion> is missing")

    return {
        "npm": str(package["version"]),
        "PyPI": str(python_project["project"]["version"]),
        "NuGet": dotnet_version,
        "NuGet consumer": consumer_version,
    }


def validate_composer_manifest() -> list[str]:
    composer = json.loads((ROOT / "composer.json").read_text(encoding="utf-8"))
    failures: list[str] = []

    if composer.get("name") != COMPOSER_NAME:
        failures.append(
            f"Composer package name is {composer.get('name')!r}, expected {COMPOSER_NAME!r}"
        )
    if "version" in composer:
        failures.append("Composer manifest must derive its version from the Git tag")
    if composer.get("autoload", {}).get("psr-4") != COMPOSER_AUTOLOAD:
        failures.append(
            "Composer PSR-4 autoload must map the public namespace to packages/php/src/"
        )

    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--tag",
        help="Release tag to compare (vMAJOR.MINOR.PATCH).",
    )
    args = parser.parse_args()

    versions = read_versions()
    expected = next(iter(versions.values()))
    failures = validate_composer_manifest()
    failures.extend(
        [
            f"{name} uses {version}, expected {expected}"
            for name, version in versions.items()
            if version != expected
        ]
    )

    if not SEMVER.fullmatch(expected):
        failures.append(f"{expected} is not a stable MAJOR.MINOR.PATCH version")

    if args.tag is not None:
        expected_tag = f"v{expected}"
        if args.tag != expected_tag:
            failures.append(
                f"tag {args.tag} does not match expected source tag {expected_tag}"
            )

    if failures:
        for failure in failures:
            print(f"ERROR: {failure}", file=sys.stderr)
        return 1

    print(f"Package versions are synchronized at {expected}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
