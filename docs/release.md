# Release process

1. Confirm the worktree contains only public engine changes.
2. Run unit tests, skill validation, the public-safety scanner and a clean wheel build.
3. Review `git ls-files` and scan the complete Git history; do not rely on `.gitignore` to remove previously committed data.
4. Keep the software version, plugin versions, tag and changelog entry aligned.
5. Create a prerelease tag such as `v0.1.0-alpha.1`.
6. Build artifacts from a clean checkout and scan the unpacked artifacts again.
7. Publish a GitHub prerelease with checksums and a clear known-limitations section.
8. Clone the public repository into a fresh temporary directory and run the five-minute quick start.

If a secret is found after publication, rotate it immediately. Deleting a file, tag or release does not revoke an exposed credential.
