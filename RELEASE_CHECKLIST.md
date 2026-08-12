# Release checklist

Version: `X.Y.Z`
Tag: `vX.Y.Z`
Source commit: `________________`
Release workflow run: `________________`

## One-time publishing setup

- [ ] GitHub environment is named `release`, restricts deployment tags to
      `v*.*.*`, and has the intended reviewer/bypass policy.
- [ ] `@manacost-labs/deckstrings` exists on npm. If it required a one-time
      pre-1.0 bootstrap, that publish used interactive 2FA and any temporary
      credential was removed; local provenance was explicitly disabled and the
      bootstrap did not use the `latest` tag.
- [ ] npm trusted publisher for `@manacost-labs/deckstrings` matches
      `Manacost-Labs/hearthstone-deckstrings`, `release.yml`, environment
      `release`, and allows `npm publish`.
- [ ] PyPI trusted publisher for `manacost-deckstrings` matches the same
      repository, workflow, and environment.
- [ ] NuGet trusted publishing policy for `ManacostLabs.Deckstrings` matches the
      same repository, workflow, and environment.
- [ ] `NUGET_USER` is set to the nuget.org profile name expected by the trusted
      publishing policy.
- [ ] No npm, PyPI, or NuGet long-lived publish token is used by the release
      workflow.
- [ ] Packagist tracks
      `Manacost-Labs/hearthstone-deckstrings-php`, not the monorepo root.
- [ ] The reviewed, SHA-pinned PHP mirror sync workflow is installed in the
      distribution repository and can run manually and hourly.

## Before publishing

- [ ] The release commit is on `main` and all required CI checks passed.
- [ ] `CHANGELOG.md` and GitHub Release notes describe the user-visible change.
- [ ] npm, PyPI, and NuGet manifests all contain `X.Y.Z`.
- [ ] `python3 scripts/check_versions.py --tag vX.Y.Z` passed.
- [ ] Shared fixture/schema validation passed.
- [ ] JavaScript lint, types, unit/browser tests, package smoke, and pack
      inspection passed.
- [ ] PHP Composer validation, compatibility/unit tests, and static analysis
      passed on supported versions.
- [ ] Python tests, typing, lint, build, and `twine check` passed on supported
      versions.
- [ ] .NET compatibility/unit tests, package validation, and pack passed for
      supported target frameworks.
- [ ] Examples passed the checks in `examples/README.md`.
- [ ] Manual `workflow_dispatch` built release artifacts and did not publish.
- [ ] Dry-run artifacts contain the correct version, readmes, license,
      types/symbols, and no source-only or secret files.

## Publish

- [ ] GitHub Release targets the verified source commit and uses the exact tag
      `vX.Y.Z`.
- [ ] The GitHub Release is published; a tag alone is not treated as a release.
- [ ] The `release` environment deployment was reviewed and approved.
- [ ] `.github/workflows/release.yml` completed successfully.
- [ ] npm OIDC publish completed and provenance is visible.
- [ ] PyPI OIDC publish completed; wheel, sdist, and attestations are visible.
- [ ] NuGet OIDC publish completed; package and symbols were accepted.
- [ ] GitHub release artifacts, checksums, and attestations are present.
- [ ] PHP mirror has the same `vX.Y.Z` tag and exported package contents.
- [ ] Packagist exposes `manacost-labs/hearthstone-deckstrings` version `X.Y.Z`.

## Fresh consumer smoke

- [ ] `npm view` returns `X.Y.Z`; a clean exact-version install round-trips a
      known deckstring.
- [ ] PyPI returns `X.Y.Z`; a clean virtual environment exact-version install
      round-trips a known deckstring.
- [ ] NuGet returns `X.Y.Z`; a clean consumer project restores and round-trips a
      known deckstring.
- [ ] Packagist returns `X.Y.Z`; a clean Composer project installs it and
      round-trips a known deckstring.
- [ ] At least one full clipboard export parses and formats through a registry
      package.
- [ ] One invalid input in each installed package exposes the expected stable
      error code rather than requiring message matching.

## Completion boundary

- [ ] The release is declared complete only after all four registry versions,
      the PHP mirror tag, provenance/attestations, and fresh consumer smoke tests
      are verified.
- [ ] Links to registry pages, workflow run, checksums, and any exception are
      recorded in the release issue or operational log.

If any upload is partial, do not move the tag or overwrite a published version.
Follow the failure procedure in [`docs/RELEASING.md`](docs/RELEASING.md#partial-or-failed-release).
