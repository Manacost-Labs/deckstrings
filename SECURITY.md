# Security policy

## Supported versions

| Version | Supported |
| --- | --- |
| Latest `1.x` release | Yes |
| Older `1.x` releases | Security fixes are delivered in the latest `1.x` |
| Historical HearthSim releases | No |

Before the first public release, the latest commit on `main` is the supported
release candidate.

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability. Use GitHub's private
vulnerability reporting for this repository, or contact a Manacost Labs
organization owner privately if GitHub reporting is unavailable.

Please include the affected language, a minimal proof of concept, impact, and
any suggested mitigation. Avoid including private Hearthstone or user data.

The parsers enforce input-size, group-size, integer, and structural limits, but
reports about denial of service, inconsistent validation, package supply-chain
issues, or unsafe parsing are still welcome.
