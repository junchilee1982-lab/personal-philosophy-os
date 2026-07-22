# Privacy model

Personal Philosophy OS is designed so that engine code and personal data remain physically separate.

## What this repository contains

- Python engine and command-line interface
- Agent skill instructions
- Public schemas and empty templates
- Small records marked `synthetic: true`
- Tests, CI and release metadata

## What it must never contain

- Real conversations, diaries or source documents
- Personal thought cards, relationship cases or decision reviews
- Real names, contact details, addresses or workplace details
- Shadow-run answers, transaction receipts or runtime logs
- Tokens, API keys, browser sessions or model request dumps

The repository safety scanner enforces these boundaries and supports a private local denylist whose contents are never committed.

## Where Vault data lives

The engine resolves a Vault from an explicit command-line path, an environment variable, user configuration, or an operating-system data directory. It does not create a Vault inside the Git repository unless the user explicitly chooses such a path.

## Network and telemetry

The engine makes no network requests and sends no telemetry. The agent host may send text to its configured language-model provider when a user asks an agent to analyze Vault material. That transfer is controlled by the host and the user's provider settings, not by this engine.

Before giving an agent access to private material, review the privacy and data-retention terms of the model provider. Prefer minimal evidence and internal IDs over copying entire source documents into prompts.

## Read and write behavior

- Search, context lookup and validation are read-only.
- Initialization and explicit mode changes write local files.
- Skill installation writes only to the selected skill directory.
- Uninstall removes only files marked as managed by this project and never deletes a Vault.
- The project never commits, pushes, synchronizes or exports Vault data automatically.

## Third-party information

Use subject IDs or aliases for other people. Store only details necessary for reasoning about responsibility, boundaries and decisions. Do not turn another person's words into the Vault owner's principles.

## Reporting a privacy issue

Use GitHub private vulnerability reporting when available. Do not paste a private Vault, secret, real conversation or identifying sample into a public Issue.
