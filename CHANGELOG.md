# Changelog

All notable changes are documented here. Software versions, Vault schema versions and rollout modes are independent concepts.

## [0.1.0-alpha.1] - 2026-07-22

### Added

- Local-first Vault initialization, validation, doctor, search and root-context commands.
- Default root-question framework with an explicit unclassified root.
- Separate evidence, mapping, principle, case, reflection and external-source layers.
- Codex and Claude Code skill packaging with deterministic install and uninstall commands.
- Synthetic demonstration Vault, public JSON Schemas and privacy-safe CI checks.

### Known limitations

- This alpha does not automate bulk extraction, model calls, nightly pipelines or cloud sync.
- Human review is still required before candidate mappings or principles become confirmed.
- The public engine does not migrate a private legacy Vault automatically.
