# Release runbook

This repository publishes one synchronized version to npm, PyPI, NuGet, and
Packagist. A release is complete only after all four registries expose the same
version and fresh consumer smoke tests pass.

The intended production path is `.github/workflows/release.yml`. Publishing is
triggered only by a published GitHub Release whose tag is exactly `vX.Y.Z`.
Manual `workflow_dispatch` runs build and inspect artifacts but must not publish
them.

## One-time publisher setup

Complete and verify these settings before creating the first release. Do not
assume that merging the workflow creates registry-side trust policies.

### GitHub environment

Create the `release` environment and:

- add a deployment branch/tag rule of type **Selected tags** with the custom
  pattern `v*.*.*`;
- require a reviewer and enable **Prevent self-review**;
- disable administrator bypass if that matches the organization policy;
- use GitHub-hosted runners for OIDC publishing;
- keep long-lived publish tokens out of repository and environment secrets.

GitHub evaluates environment protection before the publish job runs. See
[Deployments and environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments).

### npm trusted publisher

First check whether the package coordinate already exists:

```bash
npm view @manacost-labs/deckstrings name version
```

npm can add a trusted publisher only to a package that already exists. If this
lookup returns `E404`, stop the production release. An authorized maintainer
must first create the package with a reviewed bootstrap version lower than
`1.0.0` (for example `0.0.0-bootstrap.0` under a non-`latest` tag) using
interactive 2FA. Disable provenance for this local bootstrap because it does
not have GitHub Actions provenance, for example:

```bash
NPM_CONFIG_PROVENANCE=false npm publish bootstrap-package.tgz \
  --access public --tag bootstrap
```

Then configure trusted publishing and remove any temporary credential. Never
bootstrap with `1.0.0` or the `latest` tag: registry versions are immutable and
the OIDC release could not replace it. Until the bootstrap prerelease exists
and the trusted publisher is verified, the npm production release is blocked.
If project policy forbids this one-time non-OIDC bootstrap, the npm part of the
release remains blocked.

For `@manacost-labs/deckstrings`, configure a GitHub Actions trusted publisher
with these exact identity fields:

| Field | Value |
| --- | --- |
| Organization | `Manacost-Labs` |
| Repository | `hearthstone-deckstrings` |
| Workflow file | `release.yml` |
| Environment | `release` |
| Allowed action | `npm publish` |

The publish job needs `id-token: write` and a current npm CLI. npm trusted
publishing requires npm 11.5.1 or newer and Node.js 22.14.0 or newer. It does
not use `NODE_AUTH_TOKEN`; OIDC authentication happens during `npm publish`.
For a public package in a public repository, trusted publishing automatically
adds npm provenance. See [Trusted publishing for npm packages](https://docs.npmjs.com/trusted-publishers/).
The existing-package prerequisite is documented by
[`npm trust`](https://docs.npmjs.com/cli/v11/commands/npm-trust/).

### PyPI trusted publisher

For `manacost-deckstrings`, register the GitHub owner, repository,
`release.yml`, and `release` environment as a PyPI trusted publisher. The
publish job needs `id-token: write` and must not pass a username, password, or
API token to `pypa/gh-action-pypi-publish`.

The official PyPA action generates and uploads PyPI publish attestations by
default during a trusted publish. See [Publishing with a Trusted
Publisher](https://docs.pypi.org/trusted-publishers/using-a-publisher/) and
[Producing attestations](https://docs.pypi.org/attestations/producing-attestations/).

If the project does not yet exist, configure a pending publisher using the same
identity. Confirm the project owner and publisher record before release.

### NuGet trusted publisher

Under the nuget.org account or organization that owns
`ManacostLabs.Deckstrings`, create a trusted publishing policy with:

| Field | Value |
| --- | --- |
| Repository owner | `Manacost-Labs` |
| Repository | `hearthstone-deckstrings` |
| Workflow file | `release.yml` |
| Environment | `release` |

Set the required repository or `release` environment variable `NUGET_USER` to
the nuget.org profile name used by that policy (not an email address). A missing
or incorrect value is a production-release blocker.

The job requests `id-token: write`, exchanges that identity through
`NuGet/login`, and passes its short-lived `NUGET_API_KEY` output to
`dotnet nuget push`. Request the key immediately before the push; temporary
NuGet keys expire after one hour. See [Trusted publishing on
nuget.org](https://learn.microsoft.com/nuget/nuget-org/trusted-publishing).

### Packagist mirror

Packagist must track the dedicated distribution repository:

```text
https://github.com/Manacost-Labs/hearthstone-deckstrings-php
```

Do not point Packagist at the monorepo root. The mirror's sync workflow copies
`packages/php/` from this repository, mirrors stable published GitHub Releases
with tags matching `vX.Y.Z`, and updates its `main` branch. Before creating a
mirror tag, it requires the source tag commit to be contained in `main` and all
required CI checks for that exact commit to have succeeded. It runs hourly and
can be dispatched manually. Enable the Packagist GitHub hook for prompt
updates; the manual Packagist update endpoint is a fallback, not the primary
release path. See the [Packagist
API](https://packagist.org/apidoc).

## Version contract

Release tags use stable semantic versions only:

```text
vMAJOR.MINOR.PATCH
```

The tag without its leading `v` must equal all publishable manifest versions:

- `package.json`;
- `packages/python/pyproject.toml`;
- `packages/dotnet/src/ManacostLabs.Deckstrings/ManacostLabs.Deckstrings.csproj`.

Composer derives the version from the same mirrored Git tag and therefore has
no version field in `composer.json`. Unpublished, draft, prerelease, non-semver,
off-main, or exact-commit-CI-incomplete source tags are never mirrored.

Validate the contract with:

```bash
python3 scripts/check_versions.py --tag v1.0.0
```

Never move or reuse a published tag. Registry versions are immutable.

## Prepare the release

1. Start from the intended `main` commit with no unrelated local changes.
2. Update package versions, `CHANGELOG.md`, and release notes in a normal pull
   request.
3. Confirm the compatibility fixtures and schemas describe the intended public
   behavior.
4. Run the complete local verification below.
5. Merge only after required CI and review checks pass.
6. Run `.github/workflows/release.yml` with `workflow_dispatch`. Confirm that it
   builds and inspects artifacts without publishing.
7. Download the dry-run artifacts and check filenames, contents, versions,
   licenses, readmes, symbols/types, and checksums.

On a published Release, the workflow independently verifies that the tag
commit is contained in `main` and that every required language-matrix check
for that exact commit completed successfully. It also installs each built
artifact in a clean consumer before any publish job becomes eligible.

### Local verification

Use supported runtimes. A clean environment is preferred for the package
consumer checks.

```bash
uv sync --project packages/python --locked --all-extras
uv run --project packages/python --locked --all-extras python scripts/check_versions.py --tag v1.0.0
uv run --project packages/python --locked --all-extras python scripts/validate_fixtures.py

yarn install --frozen-lockfile
yarn run verify
npm pack --dry-run --json

composer --working-dir=packages/php install --no-scripts --no-plugins
composer --working-dir=packages/php validate --strict --check-lock --no-plugins
composer --working-dir=packages/php check

uv run --project packages/python --locked --all-extras pytest packages/python/tests
uv run --project packages/python --locked --all-extras mypy packages/python/src
uv run --project packages/python --locked --all-extras ruff check packages/python
uv run --project packages/python --locked --all-extras python -m build packages/python --no-isolation
uv run --project packages/python --locked --all-extras twine check packages/python/dist/*

dotnet test packages/dotnet/tests/ManacostLabs.Deckstrings.Tests/ManacostLabs.Deckstrings.Tests.csproj --configuration Release
dotnet run --project packages/dotnet/tests/ManacostLabs.Deckstrings.Compatibility/ManacostLabs.Deckstrings.Compatibility.csproj --configuration Release -- fixtures/deckstrings.json
dotnet pack packages/dotnet/src/ManacostLabs.Deckstrings/ManacostLabs.Deckstrings.csproj --configuration Release
```

Run the example verification documented in [`examples/README.md`](../examples/README.md)
as an additional consumer-level check.

## Publish

1. In GitHub, draft a new Release targeting the verified `main` commit.
2. Create or select the exact tag `vX.Y.Z`; the title should also identify
   `X.Y.Z`.
3. Paste reviewed release notes. Do not mark a stable release as a prerelease.
4. Publish the GitHub Release. Creating or pushing a tag alone does not invoke
   the production publishing path.
5. Review and approve the job waiting on the `release` environment.
6. Confirm `.github/workflows/release.yml` completed, not merely started. Check
   every build, attestation, and upload job, then run the registry smoke tests
   below.
7. Manually dispatch the mirror workflow in
   `Manacost-Labs/hearthstone-deckstrings-php`, or wait for the hourly run.
8. Confirm mirror tag `vX.Y.Z` resolves to files exported from the same source
   tag, then wait for Packagist to ingest it.

The workflow builds and uploads artifacts in a job without `id-token: write`.
A separate job downloads those completed artifacts and creates attestations;
publish jobs download the same artifact set. The attestation job requires
`contents: read`, `id-token: write`, `attestations: write`, and
`artifact-metadata: write`. Release-asset jobs separately require
`contents: write`. See [Using artifact attestations](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations).

## Registry smoke tests

Registry pages may be eventually consistent. Retry read-only lookups for a few
minutes, but do not republish an existing version.

### npm

```bash
npm view @manacost-labs/deckstrings@1.0.0 version dist.integrity dist.tarball --json

deckstrings_npm_smoke="$(mktemp -d)"
cd "$deckstrings_npm_smoke"
npm init --yes
npm install --ignore-scripts --no-audit --no-fund @manacost-labs/deckstrings@1.0.0
node --input-type=module -e 'import {decode,encode} from "@manacost-labs/deckstrings"; const value="AAEBAQcBBAMBAgMAAA=="; if (encode(decode(value)) !== value) process.exit(1)'
```

Check the npm package page for the expected source repository and provenance
record.

### PyPI

```bash
python3 -m pip index versions manacost-deckstrings

deckstrings_python_smoke="$(mktemp -d)"
python3 -m venv "$deckstrings_python_smoke/venv"
"$deckstrings_python_smoke/venv/bin/python" -m pip install --no-cache-dir manacost-deckstrings==1.0.0
"$deckstrings_python_smoke/venv/bin/python" -c 'from manacost_deckstrings import decode, encode; value="AAEBAQcBBAMBAgMAAA=="; assert encode(decode(value)) == value'
```

Confirm both the wheel and source distribution are present and the PyPI
provenance section identifies this repository and release workflow.

### NuGet

```bash
deckstrings_nuget_smoke="$(mktemp -d)"
dotnet new console --output "$deckstrings_nuget_smoke/app" --framework net8.0
dotnet add "$deckstrings_nuget_smoke/app/app.csproj" package ManacostLabs.Deckstrings --version 1.0.0
cp packages/dotnet/tests/ManacostLabs.Deckstrings.Consumer/Program.cs \
  "$deckstrings_nuget_smoke/app/Program.cs"
dotnet run --project "$deckstrings_nuget_smoke/app/app.csproj"
```

Also confirm the `.nupkg` and `.snupkg` appear on nuget.org with the expected
repository metadata.

### Packagist

```bash
composer show manacost-labs/hearthstone-deckstrings 1.0.0 --all

deckstrings_composer_smoke="$(mktemp -d)"
composer --working-dir="$deckstrings_composer_smoke" require --no-interaction --no-scripts manacost-labs/hearthstone-deckstrings:1.0.0
php -r 'require $argv[1]; $value="AAEBAQcBBAMBAgMAAA=="; $codec="ManacostLabs\\Deckstrings\\Deckstrings"; if ($codec::encode($codec::decode($value)) !== $value) exit(1);' \
  "$deckstrings_composer_smoke/vendor/autoload.php"
```

Verify that Packagist links to `Manacost-Labs/hearthstone-deckstrings-php` and
that its `1.0.0` source reference matches the mirror tag.

## Verify provenance and release assets

For artifacts attached to the GitHub Release, verify GitHub attestations:

```bash
gh attestation verify path/to/artifact \
  --repo Manacost-Labs/hearthstone-deckstrings
```

Compare downloaded artifact SHA-256 values with the checksums produced by the
release workflow. Registry-native provenance is separate: inspect npm
provenance and PyPI publish attestations on their registry pages. NuGet OIDC
proves the publishing identity, while GitHub attestations bind release
artifacts to this workflow.

## Partial or failed release

- Do not delete or overwrite a published registry version.
- Do not move `vX.Y.Z` to a different commit.
- Record which registry uploads completed and retain the original artifacts and
  checksums.
- If the workflow supports retrying only an unpublished target, use the exact
  original artifact. An already-published target must be skipped, not replaced.
- If identical artifacts cannot be proven, fix the issue and release a new
  patch version.
- A green build or one successful registry upload is not a completed release.
  Completion requires npm, PyPI, NuGet, the PHP mirror, Packagist, provenance,
  and fresh install smoke tests.

Use [`RELEASE_CHECKLIST.md`](../RELEASE_CHECKLIST.md) as the short operational
record for each release.
