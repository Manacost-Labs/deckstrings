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
