# Contributing

Thank you for helping improve Manacost Labs Hearthstone Deckstrings.

## Contract first

The public contract lives in `spec/` and `fixtures/`. Any change to decoding,
encoding, canonicalization, limits, or error behavior must update the shared
fixtures and pass in JavaScript, PHP, Python, and .NET.

Do not keep language-specific copies of fixtures.

## Pull requests

1. Create a focused branch from `main`.
2. Keep behavior changes separate from build-tool modernization.
3. Add or update shared fixtures before implementation-specific tests.
4. Run the local checks described in `README.md`.
5. Open a draft pull request and explain compatibility impact.

Public API changes must include documentation and a changelog entry. Breaking
changes require a major version according to `ROADMAP.md`.

## Required checks

Run the checks for every language you changed, plus the shared contract checks
for any behavioral change:

```bash
npm run verify
uv sync --project packages/python --locked --all-extras
uv run --project packages/python --locked python scripts/validate_fixtures.py
uv run --project packages/python --locked python scripts/check_versions.py

composer install --no-scripts --no-plugins
composer check

uv run --project packages/python --locked pytest packages/python/tests
uv run --project packages/python --locked ruff check packages/python
uv run --project packages/python --locked mypy packages/python/src

dotnet test packages/dotnet/tests/ManacostLabs.Deckstrings.Tests/ManacostLabs.Deckstrings.Tests.csproj -c Release
dotnet run --project packages/dotnet/tests/ManacostLabs.Deckstrings.Compatibility/ManacostLabs.Deckstrings.Compatibility.csproj -c Release -- fixtures/deckstrings.json
```

CI remains authoritative for the full PHP 8.2–8.5, Python 3.10–3.14, Node.js
22/24, browser, and .NET 8/10 matrix.

## Coding guidelines

- Prefer small, dependency-free implementations.
- Keep public behavior equivalent, but use idiomatic names and types per language.
- Treat deckstrings as untrusted input.
- Preserve legacy deckstrings without a sideboard marker.
- Do not add card names, images, rotations, or network access to the core codec.

## Reporting bugs

Include the language/package, runtime version, input deckstring when it is safe
to share, expected behavior, actual error code, and a minimal reproduction.

Potential security issues must follow `SECURITY.md` instead of a public issue.
