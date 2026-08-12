from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/generate_release_metadata.py"
VERSION = "1.0.0"
SOURCE_SHA = "e58286383f7849e6d3b77010baddbd311d7d23c8"
ARTIFACTS = (
    "npm/manacost-labs-deckstrings-1.0.0.tgz",
    "python/manacost_deckstrings-1.0.0-py3-none-any.whl",
    "python/manacost_deckstrings-1.0.0.tar.gz",
    "nuget/ManacostLabs.Deckstrings.1.0.0.nupkg",
    "nuget/ManacostLabs.Deckstrings.1.0.0.snupkg",
    "composer/manacost-labs-hearthstone-deckstrings-1.0.0.zip",
)


class ReleaseMetadataTests(unittest.TestCase):
    def create_artifacts(self, root: Path) -> None:
        for relative_path in ARTIFACTS:
            path = root / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(f"fixture:{relative_path}".encode())

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
                "--build-id",
                "12345-1",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_generates_complete_spdx_and_portable_checksums(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.create_artifacts(root)

            result = self.run_script(root)

            self.assertEqual(result.returncode, 0, result.stderr)
            sbom = json.loads((root / "sbom.spdx.json").read_text())
            self.assertEqual(sbom["spdxVersion"], "SPDX-2.3")
            self.assertEqual(len(sbom["packages"]), 4)
            self.assertEqual(len(sbom["files"]), 6)
            self.assertTrue(
                all(
                    {checksum["algorithm"] for checksum in file["checksums"]}
                    == {"SHA1", "SHA256"}
                    for file in sbom["files"]
                )
            )
            self.assertEqual(
                {
                    (
                        package["name"],
                        package["versionInfo"],
                        package["externalRefs"][0]["referenceLocator"],
                    )
                    for package in sbom["packages"]
                },
                {
                    (
                        "@manacost-labs/deckstrings",
                        "1.0.0",
                        "pkg:npm/%40manacost-labs/deckstrings@1.0.0",
                    ),
                    (
                        "manacost-deckstrings",
                        "1.0.0",
                        "pkg:pypi/manacost-deckstrings@1.0.0",
                    ),
                    (
                        "ManacostLabs.Deckstrings",
                        "1.0.0",
                        "pkg:nuget/ManacostLabs.Deckstrings@1.0.0",
                    ),
                    (
                        "manacost-labs/hearthstone-deckstrings",
                        "1.0.0",
                        "pkg:composer/manacost-labs/hearthstone-deckstrings@1.0.0",
                    ),
                },
            )
            distribution_relationships = {
                (relationship["spdxElementId"], relationship["relatedSpdxElement"])
                for relationship in sbom["relationships"]
                if relationship["relationshipType"] == "DISTRIBUTION_ARTIFACT"
            }
            self.assertEqual(
                distribution_relationships,
                {
                    (
                        "SPDXRef-Package-npm",
                        "SPDXRef-File-manacost-labs-deckstrings-1.0.0.tgz",
                    ),
                    (
                        "SPDXRef-Package-pypi",
                        "SPDXRef-File-manacost-deckstrings-1.0.0-py3-none-any.whl",
                    ),
                    (
                        "SPDXRef-Package-pypi",
                        "SPDXRef-File-manacost-deckstrings-1.0.0.tar.gz",
                    ),
                    (
                        "SPDXRef-Package-nuget",
                        "SPDXRef-File-ManacostLabs.Deckstrings.1.0.0.nupkg",
                    ),
                    (
                        "SPDXRef-Package-nuget",
                        "SPDXRef-File-ManacostLabs.Deckstrings.1.0.0.snupkg",
                    ),
                    (
                        "SPDXRef-Package-composer",
                        "SPDXRef-File-manacost-labs-hearthstone-deckstrings-1.0.0.zip",
                    ),
                },
            )

            lines = (root / "SHA256SUMS").read_text().splitlines()
            self.assertEqual(len(lines), 7)
            checksums = dict(line.split("  ", 1) for line in lines)
            self.assertTrue(all("/" not in filename for filename in checksums.values()))
            for relative_path in ARTIFACTS:
                path = root / relative_path
                self.assertEqual(
                    hashlib.sha256(path.read_bytes()).hexdigest(),
                    next(
                        checksum
                        for checksum, filename in checksums.items()
                        if filename == path.name
                    ),
                )

    def test_rejects_an_unexpected_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.create_artifacts(root)
            (root / "unexpected.txt").write_text("unexpected")

            result = self.run_script(root)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unexpected artifacts: unexpected.txt", result.stderr)

    def test_rejects_nested_release_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.create_artifacts(root)
            (root / "python/SHA256SUMS").write_text("unexpected")

            result = self.run_script(root)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unexpected artifacts: python/SHA256SUMS", result.stderr)


if __name__ == "__main__":
    unittest.main()
