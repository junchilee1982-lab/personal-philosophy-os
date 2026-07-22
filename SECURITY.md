# Security policy

## Supported versions

During the alpha period, only the latest tagged prerelease receives security fixes.

## Reporting a vulnerability

Use the repository's private vulnerability reporting feature. If that is unavailable, open a public Issue containing only a request for a private contact channel.

Never include secrets, private Vault records, real conversations or identifying screenshots in a public report.

## Secret exposure response

If a credential reaches a public Git history, deleting the file or Release is not sufficient. Revoke or rotate the credential first, then clean the history, invalidate affected artifacts and publish a security notice.

## Scope

Security reports may cover path traversal, unintended Vault writes or deletion, skill-install overwrite behavior, secret leakage in diagnostics, malformed JSONL handling and release-safety bypasses.
