from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from collections.abc import Callable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/verify_release_bundle.py"
VERSION = "1.0.0"
SOURCE_SHA = "e58286383f7849e6d3b77010baddbd311d7d23c8"
WRONG_SOURCE_SHA = "f" * 40
ARTIFACTS = (
    "manacost-labs-deckstrings-1.0.0.tgz",
    "manacost_deckstrings-1.0.0-py3-none-any.whl",
    "manacost_deckstrings-1.0.0.tar.gz",
    "ManacostLabs.Deckstrings.1.0.0.nupkg",
    "ManacostLabs.Deckstrings.1.0.0.snupkg",
    "manacost-labs-hearthstone-deckstrings-1.0.0.zip",
)
PACKAGE_NAMES = {
    "SPDXRef-Package-npm": "@manacost-labs/deckstrings",
    "SPDXRef-Package-pypi": "manacost-deckstrings",
    "SPDXRef-Package-nuget": "ManacostLabs.Deckstrings",
    "SPDXRef-Package-composer": "manacost-labs/hearthstone-deckstrings",
}
DISTRIBUTIONS = {
    "SPDXRef-Package-npm": (ARTIFACTS[0],),
    "SPDXRef-Package-pypi": (ARTIFACTS[1], ARTIFACTS[2]),
    "SPDXRef-Package-nuget": (ARTIFACTS[3], ARTIFACTS[4]),
    "SPDXRef-Package-composer": (ARTIFACTS[5],),
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class ReleaseBundleVerificationTests(unittest.TestCase):
    def create_bundle(self, root: Path) -> None:
        for filename in ARTIFACTS:
            (root / filename).write_bytes(f"fixture:{filename}".encode())
        self.write_sbom(root, self.valid_sbom(root))

    def valid_sbom(self, root: Path) -> dict[str, Any]:
        file_ids = {
            filename: f"SPDXRef-File-{index}"
            for index, filename in enumerate(ARTIFACTS, start=1)
        }
        return {
            "spdxVersion": "SPDX-2.3",
            "SPDXID": "SPDXRef-DOCUMENT",
            "packages": [
                {
                    "SPDXID": spdx_id,
                    "name": name,
                    "versionInfo": VERSION,
                    "sourceInfo": f"Built from Git commit {SOURCE_SHA}.",
                }
                for spdx_id, name in PACKAGE_NAMES.items()
            ],
            "files": [
                {
                    "SPDXID": file_ids[filename],
                    "fileName": f"./{filename}",
                    "checksums": [
                        {
                            "algorithm": "SHA256",
                            "checksumValue": sha256(root / filename),
                        }
                    ],
                }
                for filename in ARTIFACTS
            ],
            "relationships": [
                {
                    "spdxElementId": package_id,
                    "relationshipType": "DISTRIBUTION_ARTIFACT",
                    "relatedSpdxElement": file_ids[filename],
                }
                for package_id, filenames in DISTRIBUTIONS.items()
                for filename in filenames
            ],
        }

    def write_sbom(self, root: Path, sbom: dict[str, Any]) -> None:
        (root / "sbom.spdx.json").write_text(
            json.dumps(sbom, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        self.write_checksums(root)

    def write_checksums(self, root: Path) -> None:
        targets = (*ARTIFACTS, "sbom.spdx.json")
        lines = [f"{sha256(root / filename)}  {filename}" for filename in targets]
        (root / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")

    def mutate_sbom(
        self, root: Path, mutation: Callable[[dict[str, Any]], None]
    ) -> None:
        sbom = json.loads((root / "sbom.spdx.json").read_text(encoding="utf-8"))
        mutation(sbom)
        self.write_sbom(root, sbom)

    def run_script(self, root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--artifacts",
                str(root),
                "--version",
                VERSION,
                "--source-sha",
                SOURCE_SHA,
            ],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_accepts_exact_complete_flat_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.create_bundle(root)

            result = self.run_script(root)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(
                f"Verified release bundle for {VERSION} at commit {SOURCE_SHA}.",
                result.stdout,
            )

    def test_rejects_missing_unexpected_empty_and_nested_entries(self) -> None:
        def remove_artifact(root: Path) -> None:
            (root / ARTIFACTS[0]).unlink()

        def add_unexpected(root: Path) -> None:
            (root / "unexpected.txt").write_text("unexpected", encoding="utf-8")

        def empty_artifact(root: Path) -> None:
            (root / ARTIFACTS[0]).write_bytes(b"")

        def add_directory(root: Path) -> None:
            (root / "nested").mkdir()

        cases = (
            ("missing", remove_artifact, "missing files"),
            ("unexpected", add_unexpected, "unexpected files"),
            ("empty", empty_artifact, "empty files"),
            ("nested", add_directory, "must be flat"),
        )
        for name, mutation, expected_error in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.create_bundle(root)
                mutation(root)

                result = self.run_script(root)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_error, result.stderr)

    def test_rejects_symlinked_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.create_bundle(root)
            link = root / ARTIFACTS[0]
            link.unlink()
            try:
                os.symlink(root / ARTIFACTS[1], link)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"symlinks are unavailable: {error}")

            result = self.run_script(root)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("symlinks are not allowed", result.stderr)

    def test_rejects_inexact_or_mismatched_checksum_manifest(self) -> None:
        def missing_entry(root: Path, lines: list[str]) -> list[str]:
            return lines[:-1]

        def unexpected_entry(root: Path, lines: list[str]) -> list[str]:
            return [*lines, f"{'0' * 64}  unexpected.bin"]

        def duplicate_entry(root: Path, lines: list[str]) -> list[str]:
            return [*lines, lines[0]]

        def mismatched_digest(root: Path, lines: list[str]) -> list[str]:
            filename = lines[0].split("  ", 1)[1]
            return [f"{'0' * 64}  {filename}", *lines[1:]]

        cases = (
            ("missing", missing_entry, "missing checksum entries"),
            ("unexpected", unexpected_entry, "unexpected checksum entries"),
            ("duplicate", duplicate_entry, "duplicate SHA256SUMS entry"),
            ("mismatch", mismatched_digest, "SHA-256 mismatch"),
        )
        for name, mutation, expected_error in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.create_bundle(root)
                checksum_path = root / "SHA256SUMS"
                lines = checksum_path.read_text(encoding="utf-8").splitlines()
                checksum_path.write_text(
                    "\n".join(mutation(root, lines)) + "\n",
                    encoding="utf-8",
                )

                result = self.run_script(root)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_error, result.stderr)

    def test_rejects_invalid_spdx_counts_version_and_source_commit(self) -> None:
        def wrong_spdx(sbom: dict[str, Any]) -> None:
            sbom["spdxVersion"] = "SPDX-2.2"

        def missing_package(sbom: dict[str, Any]) -> None:
            sbom["packages"].pop()

        def missing_file(sbom: dict[str, Any]) -> None:
            sbom["files"].pop()

        def missing_distribution(sbom: dict[str, Any]) -> None:
            sbom["relationships"].pop()

        def wrong_version(sbom: dict[str, Any]) -> None:
            sbom["packages"][0]["versionInfo"] = "1.0.1"

        def wrong_source(sbom: dict[str, Any]) -> None:
            sbom["packages"][0]["sourceInfo"] = (
                f"Built from Git commit {WRONG_SOURCE_SHA}."
            )

        cases = (
            ("spdx", wrong_spdx, "spdxVersion must be SPDX-2.3"),
            ("packages", missing_package, "exactly 4 packages"),
            ("files", missing_file, "exactly 6 files"),
            (
                "distribution",
                missing_distribution,
                "exactly 6 DISTRIBUTION_ARTIFACT",
            ),
            ("version", wrong_version, "package version is not 1.0.0"),
            ("source", wrong_source, "sourceInfo does not contain exactly commit"),
        )
        for name, mutation, expected_error in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.create_bundle(root)
                self.mutate_sbom(root, mutation)

                result = self.run_script(root)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_error, result.stderr)

    def test_rejects_sbom_checksum_and_distribution_mapping_mismatch(self) -> None:
        def wrong_file_checksum(sbom: dict[str, Any]) -> None:
            sbom["files"][0]["checksums"][0]["checksumValue"] = "0" * 64

        def wrong_distribution(sbom: dict[str, Any]) -> None:
            sbom["relationships"][0]["spdxElementId"] = "SPDXRef-Package-pypi"

        cases = (
            ("file-checksum", wrong_file_checksum, "SBOM SHA256 checksum is invalid"),
            (
                "distribution-mapping",
                wrong_distribution,
                "relationships do not match release artifacts",
            ),
        )
        for name, mutation, expected_error in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.create_bundle(root)
                self.mutate_sbom(root, mutation)

                result = self.run_script(root)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_error, result.stderr)


if __name__ == "__main__":
    unittest.main()
