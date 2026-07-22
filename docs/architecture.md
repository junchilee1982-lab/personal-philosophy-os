# Architecture

Personal Philosophy OS has three deliberately separate layers.

```text
Agent skill                     Public engine                    Private Vault
intent routing and discipline  validation and retrieval        owner-controlled records
skills/personal-thought-vault  personal_philosophy_os package  resolved outside this repo
```

## Skill layer

The skill tells an agent when to load a Vault, how to distinguish the owner's words from external material, how to route a question, and which actions require explicit human confirmation. It contains no personal records.

## Engine layer

The Python engine provides deterministic operations:

- resolve a Vault path without hard-coded usernames;
- initialize a clean Vault;
- parse strict UTF-8 JSON and JSONL;
- validate IDs, roots, status, version chains and references;
- select effective append-only mappings;
- retrieve confirmed evidence or conclusions;
- assemble root-question context;
- install or uninstall the bundled skill safely.

The engine does not call a model. Reasoning remains in the agent layer; data integrity remains in deterministic code.

## Vault layer

The Vault is user-owned and lives outside the engine repository. Atomic cards remain immutable. Classification is stored in a separate mapping file, so a root framework can change without rewriting evidence.

```text
vault.json
roots.json
cards/cards.jsonl
mappings/root-mappings.jsonl
mappings/verdicts.jsonl
principles/principles.jsonl
cases/cases.jsonl
reflections/reflections.jsonl
sources/external-sources.jsonl
```

## Authority model

- Agents may propose mappings, principles and revisions.
- Only the configured owner can confirm them.
- A human-confirmed version cannot be superseded by a later AI candidate.
- Rejections live in an append-only verdict ledger; history is not rewritten.
- External material can support, challenge or provide a tool, but cannot become personal evidence automatically.

## Rollout modes

Software version, schema version and rollout mode are independent:

- `stable`: keep the owner's established route authoritative.
- `shadow`: compare a candidate route without making it authoritative.
- `active`: use the root-question engine as the active route.

Fresh Vaults start in `active`. Mode changes require `--confirm`.
