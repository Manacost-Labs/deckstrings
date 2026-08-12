# Multi-language backend roadmap

## Goal

Turn the existing TypeScript deckstring codec into a small family of native
backend packages with one compatibility contract:

- npm: TypeScript/JavaScript
- Packagist: PHP
- PyPI: Python
- NuGet: .NET/C#

Every implementation must decode the same deckstring into the same canonical
deck definition and must encode that definition into the same byte-for-byte
Base64 value.

## Product boundaries

The codec remains intentionally small and deterministic. It owns:

- Hearthstone deckstring version 1 encoding and decoding
- Wild, Standard, Classic, and Twist format values
- heroes, cards, and sideboards
- canonical ordering
- validation of the binary envelope and numeric fields
- parsing and formatting full text exports

The codec does not own card names, images, legality by patch, rotations,
collections, archetypes, or network access. Those features require a card-data
provider and should be separate packages.

## Repository model

```text
fixtures/                 Cross-language golden test vectors
spec/                     Wire format and shared JSON contract
packages/php/             Native PHP package
packages/python/          Native Python package
packages/dotnet/          Native .NET package
src/                      Existing TypeScript reference implementation
test/                     TypeScript and compatibility tests
```

The upstream `main` history is preserved. Multi-language development happens
on feature branches and is merged only after all language jobs pass.

## Compatibility contract

All packages must expose equivalent operations using idiomatic language names:

1. `decode(deckstring) -> deck`
2. `encode(deck) -> deckstring`
3. `canonicalize(deck) -> deck` (milestone 2)
4. `validate(deck) -> result` (milestone 2)
5. `parse_export(text) -> deck + metadata` (milestone 3)
6. `format_export(deck, metadata) -> text` (milestone 3)

Compatibility is behavioral rather than syntactic: native type names may
differ, but their JSON representation must match `spec/deck.schema.json`.

## Milestones

### M0 — Foundation ✅

Deliverables:

- document the version 1 wire format and canonical ordering
- publish a shared JSON Schema
- extract golden vectors for all four formats
- include pre-sideboard and sideboard vectors
- include an `n-copy` sideboard vector to catch field-order regressions
- run the existing TypeScript implementation against the shared vectors

Exit gate: the TypeScript package passes the original suite and every golden
vector round-trips byte-for-byte.

### M1 — Native codecs ✅

Deliverables:

- dependency-free PHP 8.2–8.5 codec with PSR-4 autoloading
- dependency-free Python 3.10–3.14 codec with a `src` package layout
- dependency-free .NET codec targeting `netstandard2.0`, `net8.0`, and
  `net10.0`
- language-specific tests reading the same fixture file
- CI jobs for Node.js, PHP, Python, and .NET

Exit gate: every language decodes every fixture to the same canonical model and
re-encodes it to the fixture's exact deckstring.

### M2 — Stable public API and validation ✅

Deliverables:

- typed deck/card/sideboard models where appropriate
- stable exception hierarchy and documented error categories
- explicit limits for hostile or unbounded input
- duplicate DBF ID policy
- canonicalization and validation APIs
- malformed Base64, truncated varint, invalid version/format, invalid count,
  and invalid sideboard-owner fixtures

Exit gate: error categories and canonicalization results are consistent across
all languages. Backward-compatibility behavior is documented.

### M3 — Full Hearthstone text export ✅

Deliverables:

- parse comments and the `### deck name` line
- format a full clipboard export
- preserve optional metadata outside the binary deckstring
- locale-neutral core API with injectable card-name resolution

Exit gate: full exports round-trip without changing the embedded deckstring.

### M4 — Packaging and releases ✅

Deliverables:

- npm, Packagist, PyPI, and NuGet package metadata
- automated subtree splits for registries such as Packagist that require the
  package manifest at the repository root
- read-only release repositories only if a registry cannot consume this
  monorepo directly; this fork remains the source of truth
- reproducible package builds
- changelog generation and release checklist
- provenance/SBOM where supported
- dry-run package validation in CI

Exit gate: all four artifacts install in clean test environments and pass a
consumer smoke test before publishing.

### M5 — First public release

Deliverables:

- synchronized `1.0.0` API contract for the new native packages
- migration guide from `deckstrings`, `python-hearthstone`, and `HearthDb`
- documentation examples for Laravel, Django/FastAPI, ASP.NET, and Node.js
- GitHub release and synchronized `v1.0.0` tag

Exit gate: no known cross-language fixture mismatches and release artifacts are
verified from their public registries.

## Versioning policy

- The shared behavioral contract follows semantic versioning.
- Package versions advance together while the APIs stabilize.
- Adding fixtures for already-supported valid input is a patch change.
- Changing validation behavior is at least a minor change and must be called
  out in the changelog.
- Removing accepted input or changing the canonical JSON model is a major
  change.

## CI and release gates

Every pull request must run:

- TypeScript build, type-check, original tests, and shared fixtures
- PHP syntax check and shared fixtures on supported PHP versions
- Python unit tests and package build
- .NET build, shared fixtures, and `dotnet pack`
- JSON Schema validation for the fixture file

Registry publication is not part of ordinary CI. It runs only from a published
GitHub Release, uses the protected `release` environment, and exchanges GitHub
OIDC identity for short-lived npm, PyPI, and NuGet credentials. A manual
workflow run builds, tests, attests, and uploads artifacts without publishing.

## Known risks

- Cross-registry publication is not atomic, so every publisher and package name
  must be verified before creating the public GitHub release.
- A brand-new npm package needs a one-time authenticated bootstrap publication
  before trusted OIDC publishing can be configured.
- Old valid deckstrings may omit the sideboard marker; the compatibility suite
  must retain that legacy fixture permanently.
- Card data and patch legality remain external dependencies of consumers and
  are intentionally not covered by the codec contract.

## Remaining release gate

M0–M4 are implemented. M5 is complete only when the same version can be
installed from npm, Packagist, PyPI, and NuGet in clean consumers and the public
artifacts match the GitHub release checksums and attestations. The operational
steps are tracked in [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md).
