#!/usr/bin/env python3
"""Generate a strict SPDX SBOM and portable checksums for release artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

REPOSITORY = "Manacost-Labs/deckstrings"
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
SOURCE_SHA = re.compile(r"^[0-9a-f]{40}$")
BUILD_ID = re.compile(r"^[A-Za-z0-9._-]+$")


@dataclass(frozen=True)
class Component:
    spdx_id: str
    name: str
    purl: str
    artifact_templates: tuple[str, ...]
    primary_artifact_template: str

    def artifact_paths(self, version: str) -> tuple[str, ...]:
        return tuple(
            template.format(version=version) for template in self.artifact_templates
        )

    def primary_artifact(self, version: str) -> str:
        return self.primary_artifact_template.format(version=version)


COMPONENTS = (
    Component(
        spdx_id="SPDXRef-Package-npm",
        name="@manacost-labs/deckstrings",
        purl="pkg:npm/%40manacost-labs/deckstrings@{version}",
        artifact_templates=("npm/manacost-labs-deckstrings-{version}.tgz",),
        primary_artifact_template="npm/manacost-labs-deckstrings-{version}.tgz",
    ),
    Component(
        spdx_id="SPDXRef-Package-pypi",
        name="manacost-deckstrings",
        purl="pkg:pypi/manacost-deckstrings@{version}",
        artifact_templates=(
            "python/manacost_deckstrings-{version}-py3-none-any.whl",
            "python/manacost_deckstrings-{version}.tar.gz",
        ),
        primary_artifact_template=(
            "python/manacost_deckstrings-{version}-py3-none-any.whl"
        ),
    ),
    Component(
        spdx_id="SPDXRef-Package-nuget",
        name="ManacostLabs.Deckstrings",
        purl="pkg:nuget/ManacostLabs.Deckstrings@{version}",
        artifact_templates=(
            "nuget/ManacostLabs.Deckstrings.{version}.nupkg",
            "nuget/ManacostLabs.Deckstrings.{version}.snupkg",
        ),
        primary_artifact_template="nuget/ManacostLabs.Deckstrings.{version}.nupkg",
    ),
    Component(
        spdx_id="SPDXRef-Package-composer",
        name="manacost-labs/hearthstone-deckstrings",
        purl="pkg:composer/manacost-labs/hearthstone-deckstrings@{version}",
        artifact_templates=(
            "composer/manacost-labs-hearthstone-deckstrings-{version}.zip",
        ),
        primary_artifact_template=(
            "composer/manacost-labs-hearthstone-deckstrings-{version}.zip"
        ),
    ),
)


def digest(path: Path, algorithm: str = "sha256") -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def file_spdx_id(filename: str) -> str:
    safe_name = re.sub(r"[^A-Za-z0-9.-]", "-", filename)
    return f"SPDXRef-File-{safe_name}"


def validate_inputs(
    artifacts: Path, version: str, source_sha: str, build_id: str
) -> dict[str, Path]:
    if not SEMVER.fullmatch(version):
        raise ValueError("version must be a stable MAJOR.MINOR.PATCH value")
    if not SOURCE_SHA.fullmatch(source_sha):
        raise ValueError("source SHA must be a lowercase 40-character Git SHA-1")
    if not BUILD_ID.fullmatch(build_id):
        raise ValueError("build ID contains unsupported characters")
    if not artifacts.is_dir():
        raise ValueError(f"artifact directory does not exist: {artifacts}")

    expected = {
        artifact_path
        for component in COMPONENTS
        for artifact_path in component.artifact_paths(version)
    }
    actual: dict[str, Path] = {}
    for path in artifacts.rglob("*"):
        if not path.is_file():
            continue
        relative_path = path.relative_to(artifacts).as_posix()
        if relative_path in {"SHA256SUMS", "sbom.spdx.json"}:
            continue
        if path.is_symlink():
            raise ValueError(f"release artifact must not be a symlink: {path}")
        actual[relative_path] = path

    missing = sorted(expected - actual.keys())
    unexpected = sorted(actual.keys() - expected)
    if missing or unexpected:
        details = []
        if missing:
            details.append(f"missing artifacts: {', '.join(missing)}")
        if unexpected:
            details.append(f"unexpected artifacts: {', '.join(unexpected)}")
        raise ValueError("; ".join(details))

    basenames = [path.name for path in actual.values()]
    if len(basenames) != len(set(basenames)):
        raise ValueError("artifact basenames must be unique for GitHub Release assets")
    empty = sorted(name for name, path in actual.items() if path.stat().st_size == 0)
    if empty:
        raise ValueError(f"empty artifacts: {', '.join(empty)}")
    return actual


def build_sbom(
    artifacts: dict[str, Path], version: str, source_sha: str, build_id: str
) -> dict[str, object]:
    release_base = f"https://github.com/{REPOSITORY}/releases/download/v{version}"
    file_ids = {
        relative_path: file_spdx_id(path.name)
        for relative_path, path in artifacts.items()
    }
    packages = []
    files = []
    relationships = []

    for relative_path, path in sorted(artifacts.items()):
        files.append(
            {
                "SPDXID": file_ids[relative_path],
                "fileName": f"./{path.name}",
                "checksums": [
                    {
                        "algorithm": "SHA1",
                        "checksumValue": digest(path, "sha1"),
                    },
                    {"algorithm": "SHA256", "checksumValue": digest(path)},
                ],
                "fileTypes": ["ARCHIVE"],
                "licenseConcluded": "NOASSERTION",
                "copyrightText": "NOASSERTION",
            }
        )

    for component in COMPONENTS:
        primary_artifact = component.primary_artifact(version)
        primary_filename = artifacts[primary_artifact].name
        packages.append(
            {
                "SPDXID": component.spdx_id,
                "name": component.name,
                "versionInfo": version,
                "downloadLocation": f"{release_base}/{primary_filename}",
                "filesAnalyzed": False,
                "licenseConcluded": "NOASSERTION",
                "licenseDeclared": "ISC",
                "copyrightText": "NOASSERTION",
                "supplier": "Organization: Manacost Labs",
                "homepage": f"https://github.com/{REPOSITORY}",
                "packageFileName": primary_filename,
                "primaryPackagePurpose": "LIBRARY",
                "sourceInfo": f"Built from Git commit {source_sha}.",
                "externalRefs": [
                    {
                        "referenceCategory": "PACKAGE-MANAGER",
                        "referenceType": "purl",
                        "referenceLocator": component.purl.format(version=version),
                    }
                ],
            }
        )
        relationships.append(
            {
                "spdxElementId": "SPDXRef-DOCUMENT",
                "relationshipType": "DESCRIBES",
                "relatedSpdxElement": component.spdx_id,
            }
        )
        for artifact_path in component.artifact_paths(version):
            relationships.append(
                {
                    "spdxElementId": component.spdx_id,
                    "relationshipType": "DISTRIBUTION_ARTIFACT",
                    "relatedSpdxElement": file_ids[artifact_path],
                }
            )
    created = (
        datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )
    return {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"Manacost Labs Hearthstone Deckstrings {version} release",
        "documentNamespace": (
            f"https://github.com/{REPOSITORY}/sbom/{version}/{source_sha}/{build_id}"
        ),
        "creationInfo": {
            "created": created,
            "creators": [
                "Organization: Manacost Labs",
                "Tool: scripts/generate_release_metadata.py",
            ],
        },
        "documentDescribes": [component.spdx_id for component in COMPONENTS],
        "packages": packages,
        "files": files,
        "relationships": relationships,
    }


def write_checksums(artifacts_dir: Path, artifacts: dict[str, Path]) -> None:
    checksum_paths = list(artifacts.values()) + [artifacts_dir / "sbom.spdx.json"]
    lines = [
        f"{digest(path)}  {path.name}"
        for path in sorted(checksum_paths, key=lambda candidate: candidate.name)
    ]
    (artifacts_dir / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", required=True, type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--build-id", required=True)
    args = parser.parse_args()

    try:
        artifacts_dir = args.artifacts.resolve(strict=True)
        artifacts = validate_inputs(
            artifacts_dir, args.version, args.source_sha, args.build_id
        )
        sbom = build_sbom(artifacts, args.version, args.source_sha, args.build_id)
        (artifacts_dir / "sbom.spdx.json").write_text(
            json.dumps(sbom, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        write_checksums(artifacts_dir, artifacts)
    except (OSError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(
        f"Generated release metadata for {len(artifacts)} artifacts "
        f"and {len(COMPONENTS)} packages."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
