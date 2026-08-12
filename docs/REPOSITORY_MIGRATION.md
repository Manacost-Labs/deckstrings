# Repository migration ledger

This document records the one-time move to the independent Manacost Labs
monorepo. It is an attribution and operational ledger, not a release tag.

## Repositories

- Target source of truth: `Manacost-Labs/deckstrings`.
- Previous source repository: `Manacost-Labs/hearthstone-deckstrings`.
- Previous Composer distribution repository:
  `Manacost-Labs/hearthstone-deckstrings-php`.
- Original upstream:
  [HearthSim/hearthstone-deckstrings](https://github.com/HearthSim/hearthstone-deckstrings).

The target is an independent GitHub repository, not a member of the HearthSim
fork network. The transfer preserves the original authorship, commit
timestamps, ISC license, and full reachable Git history.

## Verified baseline

- Source `main` before the identity migration:
  `1a5b9135867027e49ff9eefed120924a50ee24ca`.
- Successful pre-migration release dry-run: GitHub Actions run
  `31640002151`.
- Verified target `main` after the initial history transfer:
  `1a5b9135867027e49ff9eefed120924a50ee24ca` (121 commits).
- Verified transferred refs: all 19 historical tags. A fresh mirror clone
  contains 123 commits reachable from `main` plus those tags, including the two
  commits reachable only through historical tags, and passes `git fsck --full`.
- No Manacost `v1.0.0` release existed at the baseline; the first stable release
  must be created only from the independent repository after its own CI and
  release dry-run succeed.

## GitHub metadata boundary

Git preserves source files, commits, tags, author identities, and timestamps.
GitHub pull-request discussions, review records, check runs, deployments, and
Actions run URLs are repository-owned records and cannot be recreated by a Git
push. Their old URLs will stop resolving after the previous repositories are
deleted. The baseline SHA and dry-run ID above retain the minimum audit trail;
the detailed PR and settings export should be stored with the migration
operations record before deletion.

Branch protection, the `release` environment, reviewer policy, security
features, repository variables, and registry trusted-publisher records must be
recreated for `Manacost-Labs/deckstrings`. A successful run in the previous
repository does not satisfy the release gate in the target repository.

## Retirement scope and gate

The deletion scope is strictly limited to these two repositories:

1. `Manacost-Labs/hearthstone-deckstrings`
2. `Manacost-Labs/hearthstone-deckstrings-php`

No other Manacost Labs repository is included. Delete neither repository until
the target history and tags are verified, all registry metadata points at the
target, the stable version is available from npm, PyPI, NuGet, and Packagist,
and clean consumer smoke tests pass for all four packages. Repository deletion
does not create a redirect, so the exported operations record must be retained
outside the repositories being removed.
