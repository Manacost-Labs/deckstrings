#!/usr/bin/env python3
"""Verify a flat release bundle before attestation or publication."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
SOURCE_SHA = re.compile(r"^[0-9a-f]{40}$")
SOURCE_SHA_IN_TEXT = re.compile(r"(?<![0-9a-f])[0-9a-f]{40}(?![0-9a-f])")
CHECKSUM_LINE = re.compile(r"^([0-9a-f]{64})  ([^/\\\r\n]+)$")

ARTIFACT_TEMPLATES = (
    "manacost-labs-deckstrings-{version}.tgz",
    "manacost_deckstrings-{version}-py3-none-any.whl",
    "manacost_deckstrings-{version}.tar.gz",
    "ManacostLabs.Deckstrings.{version}.nupkg",
    "ManacostLabs.Deckstrings.{version}.snupkg",
    "manacost-labs-hearthstone-deckstrings-{version}.zip",
)

PACKAGE_NAMES = {
    "SPDXRef-Package-npm": "@manacost-labs/deckstrings",
    "SPDXRef-Package-pypi": "manacost-deckstrings",
    "SPDXRef-Package-nuget": "ManacostLabs.Deckstrings",
    "SPDXRef-Package-composer": "manacost-labs/hearthstone-deckstrings",
}

DISTRIBUTION_TEMPLATES = {
    "SPDXRef-Package-npm": ("manacost-labs-deckstrings-{version}.tgz",),
    "SPDXRef-Package-pypi": (
        "manacost_deckstrings-{version}-py3-none-any.whl",
        "manacost_deckstrings-{version}.tar.gz",
    ),
    "SPDXRef-Package-nuget": (
        "ManacostLabs.Deckstrings.{version}.nupkg",
        "ManacostLabs.Deckstrings.{version}.snupkg",
    ),
    "SPDXRef-Package-composer": (
        "manacost-labs-hearthstone-deckstrings-{version}.zip",
    ),
}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def expected_artifacts(version: str) -> tuple[str, ...]:
    return tuple(template.format(version=version) for template in ARTIFACT_TEMPLATES)


def validate_directory(bundle: Path, expected: set[str]) -> None:
    if bundle.is_symlink():
        raise ValueError(f"release bundle directory must not be a symlink: {bundle}")
    if not bundle.is_dir():
        raise ValueError(f"release bundle directory does not exist: {bundle}")

    entries = list(bundle.iterdir())
    symlinks = sorted(entry.name for entry in entries if entry.is_symlink())
    if symlinks:
        raise ValueError(f"symlinks are not allowed: {', '.join(symlinks)}")

    non_files = sorted(entry.name for entry in entries if not entry.is_file())
    if non_files:
        raise ValueError(f"release bundle must be flat: {', '.join(non_files)}")

    actual = {entry.name for entry in entries}
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    if missing or unexpected:
        details = []
        if missing:
            details.append(f"missing files: {', '.join(missing)}")
        if unexpected:
            details.append(f"unexpected files: {', '.join(unexpected)}")
        raise ValueError("; ".join(details))

    empty = sorted(name for name in expected if (bundle / name).stat().st_size == 0)
    if empty:
        raise ValueError(f"empty files: {', '.join(empty)}")


def parse_checksums(path: Path, expected: set[str]) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    checksums: dict[str, str] = {}
    for line_number, line in enumerate(lines, start=1):
        match = CHECKSUM_LINE.fullmatch(line)
        if match is None:
            raise ValueError(f"invalid SHA256SUMS line {line_number}")
        checksum, filename = match.groups()
        if filename in checksums:
            raise ValueError(f"duplicate SHA256SUMS entry: {filename}")
        checksums[filename] = checksum

    actual = set(checksums)
    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)
    if missing or unexpected:
        details = []
        if missing:
            details.append(f"missing checksum entries: {', '.join(missing)}")
        if unexpected:
            details.append(f"unexpected checksum entries: {', '.join(unexpected)}")
        raise ValueError("; ".join(details))
    return checksums


def validate_checksums(bundle: Path, artifact_names: tuple[str, ...]) -> None:
    checksum_targets = set(artifact_names) | {"sbom.spdx.json"}
    checksums = parse_checksums(bundle / "SHA256SUMS", checksum_targets)
    mismatches = sorted(
        filename
        for filename, expected_digest in checksums.items()
        if digest(bundle / filename) != expected_digest
    )
    if mismatches:
        raise ValueError(f"SHA-256 mismatch: {', '.join(mismatches)}")


def reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key in SBOM: {key}")
        result[key] = value
    return result


def require_list(value: object, field: str) -> list[object]:
    if not isinstance(value, list):
        raise TypeError(f"SBOM {field} must be an array")
    return value


def validate_packages(sbom: dict[str, Any], version: str, source_sha: str) -> None:
    packages = require_list(sbom.get("packages"), "packages")
    if len(packages) != 4:
        raise ValueError(f"SBOM must contain exactly 4 packages, found {len(packages)}")

    by_id: dict[str, dict[str, Any]] = {}
    for package in packages:
        if not isinstance(package, dict):
            raise TypeError("every SBOM package must be an object")
        spdx_id = package.get("SPDXID")
        if not isinstance(spdx_id, str) or spdx_id in by_id:
            raise ValueError("SBOM package SPDXIDs must be present and unique")
        by_id[spdx_id] = package

    if set(by_id) != set(PACKAGE_NAMES):
        raise ValueError("SBOM package identities do not match the release packages")

    for spdx_id, expected_name in PACKAGE_NAMES.items():
        package = by_id[spdx_id]
        if package.get("name") != expected_name:
            raise ValueError(f"SBOM package name is invalid for {spdx_id}")
        if package.get("versionInfo") != version:
            raise ValueError(f"SBOM package version is not {version}: {expected_name}")
        source_info = package.get("sourceInfo")
        if not isinstance(source_info, str) or SOURCE_SHA_IN_TEXT.findall(
            source_info
        ) != [source_sha]:
            raise ValueError(
                "SBOM package sourceInfo does not contain exactly commit "
                f"{source_sha}: "
                f"{expected_name}"
            )


def validate_files(
    sbom: dict[str, Any], bundle: Path, artifact_names: tuple[str, ...]
) -> dict[str, str]:
    files = require_list(sbom.get("files"), "files")
    if len(files) != 6:
        raise ValueError(f"SBOM must contain exactly 6 files, found {len(files)}")

    id_by_filename: dict[str, str] = {}
    expected = set(artifact_names)
    for file_entry in files:
        if not isinstance(file_entry, dict):
            raise TypeError("every SBOM file must be an object")
        spdx_id = file_entry.get("SPDXID")
        file_name = file_entry.get("fileName")
        if not isinstance(spdx_id, str) or not isinstance(file_name, str):
            raise TypeError("SBOM files must contain SPDXID and fileName strings")
        if not file_name.startswith("./") or "/" in file_name[2:]:
            raise ValueError(
                f"SBOM fileName must identify a flat artifact: {file_name}"
            )
        filename = file_name[2:]
        if filename in id_by_filename or spdx_id in id_by_filename.values():
            raise ValueError("SBOM file names and SPDXIDs must be unique")
        id_by_filename[filename] = spdx_id

        if filename not in expected:
            continue

        checksums = require_list(file_entry.get("checksums"), "file checksums")
        sha256_values = [
            checksum.get("checksumValue")
            for checksum in checksums
            if isinstance(checksum, dict) and checksum.get("algorithm") == "SHA256"
        ]
        if sha256_values != [digest(bundle / filename)]:
            raise ValueError(f"SBOM SHA256 checksum is invalid for {filename}")

    if set(id_by_filename) != expected:
        raise ValueError("SBOM file names do not match the six release artifacts")
    return id_by_filename


def validate_distribution_relationships(
    sbom: dict[str, Any], file_ids: dict[str, str], version: str
) -> None:
    relationships = require_list(sbom.get("relationships"), "relationships")
    distribution = [
        relationship
        for relationship in relationships
        if isinstance(relationship, dict)
        and relationship.get("relationshipType") == "DISTRIBUTION_ARTIFACT"
    ]
    if len(distribution) != 6:
        raise ValueError(
            "SBOM must contain exactly 6 DISTRIBUTION_ARTIFACT relationships, "
            f"found {len(distribution)}"
        )

    actual = {
        (
            relationship.get("spdxElementId"),
            relationship.get("relatedSpdxElement"),
        )
        for relationship in distribution
    }
    expected = {
        (package_id, file_ids[template.format(version=version)])
        for package_id, templates in DISTRIBUTION_TEMPLATES.items()
        for template in templates
    }
    if actual != expected or len(actual) != 6:
        raise ValueError(
            "SBOM DISTRIBUTION_ARTIFACT relationships do not match release artifacts"
        )


def validate_sbom(
    path: Path,
    bundle: Path,
    artifact_names: tuple[str, ...],
    version: str,
    source_sha: str,
) -> None:
    loaded = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_json_keys,
    )
    if not isinstance(loaded, dict):
        raise TypeError("SBOM root must be an object")
    if loaded.get("spdxVersion") != "SPDX-2.3":
        raise ValueError("SBOM spdxVersion must be SPDX-2.3")

    validate_packages(loaded, version, source_sha)
    file_ids = validate_files(loaded, bundle, artifact_names)
    validate_distribution_relationships(loaded, file_ids, version)


def verify_release_bundle(bundle: Path, version: str, source_sha: str) -> None:
    if not SEMVER.fullmatch(version):
        raise ValueError("version must be a stable MAJOR.MINOR.PATCH value")
    if not SOURCE_SHA.fullmatch(source_sha):
        raise ValueError("source SHA must be a lowercase 40-character Git SHA-1")

    artifact_names = expected_artifacts(version)
    expected_files = set(artifact_names) | {"SHA256SUMS", "sbom.spdx.json"}
    validate_directory(bundle, expected_files)
    validate_checksums(bundle, artifact_names)
    validate_sbom(
        bundle / "sbom.spdx.json",
        bundle,
        artifact_names,
        version,
        source_sha,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--artifacts",
        "--bundle",
        dest="artifacts",
        required=True,
        type=Path,
        help="Flat release bundle directory.",
    )
    parser.add_argument("--version", required=True)
    parser.add_argument("--source-sha", required=True)
    args = parser.parse_args()

    try:
        verify_release_bundle(args.artifacts, args.version, args.source_sha)
    except (OSError, TypeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(f"Verified release bundle for {args.version} at commit {args.source_sha}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
