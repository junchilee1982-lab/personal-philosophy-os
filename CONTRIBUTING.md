# Contributing

Thank you for improving Personal Philosophy OS.

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
python -m unittest discover -s tests -v
```

Before opening a pull request, run:

```bash
python scripts/check_public_safety.py --all
python scripts/validate_skill.py skills/personal-thought-vault
python -m pip wheel . --no-deps --wheel-dir dist
```

## Data rule

Never use a real Vault as a test fixture. Every tracked JSONL example must contain `"synthetic": true`, use generic subject IDs such as `person:self` or `person:friend`, and avoid real contact or identity details.

## Change design

- Preserve the separation between engine, skill and user-owned Vault.
- Keep default analysis read-only.
- Do not let AI-authored candidates override human-confirmed records.
- Treat JSONL as UTF-8 records separated only by the newline byte.
- Add a regression test for every bug fix.

## Pull requests

Keep changes focused, explain user impact, list validation commands, and call out any schema or privacy-boundary change explicitly.
