# Assets Guide

Use this guide when writing evidence records, research notes, session records, plans, and promotion notes.

This guide is the operational rule source for assets. It applies Evidence Promotion, Present-Tense Doctrine, and One Fact One Home.

## Role

`assets/` preserves how the project learned something: what was considered, what was tried, what was observed, and what raw material supports a decision. It is not live doctrine.

Default buckets:

- `assets/sessions/` - dated session records and handoffs;
- `assets/plans/` - plans, options, migration proposals, discarded approaches;
- `assets/research/` - research, source notes, explorations, comparisons, raw findings.

Create another bucket only when a repeated evidence type earns a stable home.

## What Does Not Belong

Do not use assets for current law, current constraints, domain models, repeatable procedures, capability contracts, readiness claims, secrets, local configuration, or open work queues.

If an asset contains a durable conclusion, promote the conclusion into the live owner and keep the asset as evidence.

## Naming

Use dates for historical records:

```text
assets/sessions/2026-07-07_contextkit-doctrine-expansion.md
assets/plans/2026-07-07_contextkit-migration-plan.md
assets/research/2026-07-07_host-runtime-surfaces.md
```

Use stable lowercase kebab-case for durable reference assets that are not event records.

## Body Shape

Recommended shape:

```markdown
# 2026-07-07 Topic

Purpose: why this record exists.

## Context

Question or work being recorded.

## Evidence

Raw findings, notes, observations, logs, or links.

## Durable Conclusions

Facts promoted, or ready to promote, into live context.

## Open Questions

Unresolved questions, not live doctrine.
```

If the current tool requires front matter for audits, add routing metadata without turning the asset into live doctrine.

## Promotion

1. Identify the durable conclusion.
2. Find the live owner.
3. Write the conclusion there in present tense.
4. Keep the asset as evidence.
5. Remove live duplicates.
6. Run validation.
