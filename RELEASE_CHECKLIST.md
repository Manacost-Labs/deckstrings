# Release checklist

Version: `1.0.0`
Tag: `v1.0.0`
Authoritative source/run evidence: [release issue #10](https://github.com/Manacost-Labs/deckstrings/issues/10)

This checklist is the live operational record for the first production release.
Do not check an item from intent or configuration alone; record the current SHA,
run URL, registry URL, and consumer evidence when that item is verified.

## One-time publishing setup

- [ ] GitHub environment is named `release`, restricts deployment tags to
      `v*.*.*`, and has the intended reviewer/bypass policy.
- [ ] GitHub environment `release-staging` is restricted to `main` and has no
      registry credentials or publisher identity.
- [ ] Repository immutable releases are enabled before the draft is published.
- [ ] `@manacost-labs/deckstrings` exists on npm. If it required a one-time
      pre-1.0 bootstrap, that publish used interactive 2FA and any temporary
      credential was removed; local provenance was explicitly disabled and the
      bootstrap did not use the `latest` tag.
- [ ] npm trusted publisher for `@manacost-labs/deckstrings` matches
      `Manacost-Labs/deckstrings`, `release.yml`, environment
      `release`, and allows `npm publish`.
- [ ] PyPI trusted publisher for `manacost-deckstrings` matches the same
      repository, workflow, and environment.
- [ ] NuGet trusted publishing policy for `ManacostLabs.Deckstrings` matches the
      same repository, workflow, and environment.
- [ ] `NUGET_USER` is set to the nuget.org profile name expected by the trusted
      publishing policy.
- [ ] No npm, PyPI, or NuGet long-lived publish token is used by the release
      workflow.
- [ ] Packagist tracks the root package manifest in
      `Manacost-Labs/deckstrings` and exposes the expected `dev-main` source.
- [ ] The Packagist update policy is recorded: manual update after the release
      workflow, or an accepted automatic-update partial-release risk.

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
- [ ] A second manual run with `draft_tag=v1.0.0` staged the exact eight files
      in the existing draft without overwriting assets.
- [ ] Dry-run artifacts contain the correct version, readmes, license,
      types/symbols, and no source-only or secret files.

## Publish

- [ ] GitHub Release targets the verified source commit and uses the exact tag
      `v1.0.0`.
- [ ] The release is stable (`prerelease` is false); the workflow rejects a
      prerelease event before any publish job becomes eligible.
- [ ] The GitHub Release is published; a tag alone is not treated as a release.
- [ ] The published Release reports `isImmutable=true`; its release attestation
      and all eight asset attestations verify.
- [ ] The `release` environment deployment was reviewed and approved.
- [ ] `.github/workflows/release.yml` completed successfully.
- [ ] npm OIDC publish completed and provenance is visible.
- [ ] PyPI OIDC publish completed; wheel, sdist, and attestations are visible.
- [ ] NuGet OIDC publish completed; package and symbols were accepted.
- [ ] A rerun does not hide an existing NuGet version as success; duplicate
      package uploads remain a hard failure unless identical public bytes were
      independently verified and the target job is intentionally skipped.
- [ ] GitHub release artifacts, checksums, and attestations are present.
- [ ] npm, PyPI, and NuGet jobs consumed `published-release-artifacts` downloaded
      from the immutable GitHub Release, not a second build.
- [ ] Packagist source reference matches the `Manacost-Labs/deckstrings`
      `v1.0.0` tag commit.
- [ ] Packagist exposes `manacost-labs/hearthstone-deckstrings` version `1.0.0`.

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
      provenance/attestations, and fresh consumer smoke tests are verified.
- [ ] Links to registry pages, workflow run, checksums, and any exception are
      recorded in the release issue or operational log.

If any upload is partial, do not move the tag or overwrite a published version.
Follow the failure procedure in [`docs/RELEASING.md`](docs/RELEASING.md#partial-or-failed-release).
