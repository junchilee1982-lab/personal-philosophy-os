# Data model

Public JSON Schemas live in `schemas/`. Runtime validation is implemented without third-party dependencies so the CLI works in a fresh Python environment.

## Atomic card

An atomic card records one expression or decision attributable to one subject. It can prove that the subject said or did something; it cannot by itself prove a stable personality conclusion.

Required fields include `id`, `kind`, `subject_id`, `text`, `status`, `evidence_grade`, `created_at` and `synthetic`. Real Vaults normally set `synthetic` to `false`; every tracked example in this repository must set it to `true`.

## Root mapping

Mappings are append-only and external to cards. Each version has exactly one primary root and zero or more secondary roots up to the configured maximum.

The unclassified root cannot be secondary. When it is primary, secondary roots must be empty and uncertain suggestions belong in `candidate_roots`.

Effective-selection order:

1. Remove mapping versions rejected by the latest applicable verdict.
2. If any confirmed version remains, select the highest confirmed version.
3. Otherwise select the highest AI candidate only when candidate context is requested.

## Principle

A principle links a statement to evidence, conditions, extreme cost, opposing principles, revisions and cases. A confirmed principle must identify the owner who confirmed it. External material may appear only in external-reference fields, never as personal evidence.

## Problem case

A case preserves minimal facts, responsibility, boundaries, motivation, cost, action, result, transfer signals and failure conditions. Similar cases are matched by reasoning structure, not merely by names or keywords.

## Decision reflection

The seven-part reflection separates information available at decision time from later outcomes:

1. facts known then;
2. judgment then;
3. action;
4. expected result;
5. actual result;
6. what held and what distorted;
7. revision proposal.

This prevents good luck from being mistaken for good judgment and bad luck from being mistaken for a bad decision.

## External source

External text, agent interpretation and owner interpretation have distinct fields. Acceptance is explicit and append-only. Reading, quoting or using an external framework does not make it the owner's principle.
