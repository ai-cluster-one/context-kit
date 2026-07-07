# Assets Guide

Asset authoring, evidence records, research notes, session records, and
promotion from evidence into live context.

`assets/` is the evidence layer. It preserves how the project learned something,
what was considered, what was tried, and what raw material supports a decision.
It is not the live source of truth.

## What Belongs Here

Default buckets:

- `assets/sessions/` - dated session records, handoffs, summaries of work done.
- `assets/plans/` - implementation plans, design options, migration plans,
  discarded approaches, project proposals.
- `assets/research/` - external research, source notes, exploration results,
  comparison tables, raw findings.

Create another bucket only when a repeated evidence type needs a stable home.
Name it for the evidence type, not for one task.

ContextKit's own audit reports are not assets. `contextkit audit --write`
persists them under `.contextkit/audits/`.

## What Does Not Belong Here

Do not use `assets/` for:

- current project law or constraints;
- identity, people, service maps, or domain models that future sessions must
  treat as true;
- repeatable procedures;
- capability command contracts, schemas, readiness claims, or credential rules;
- open work queues that belong in the project's work system;
- secrets or filled local configuration.

If an asset contains a durable conclusion, promote that conclusion into the
owning `context/` file and leave the asset as evidence.

## Naming

Use dates for historical records:

```text
assets/sessions/2026-07-07_contextkit-doctrine-expansion.md
assets/plans/2026-07-07_contextkit-migration-plan.md
assets/research/2026-07-07_host-runtime-surfaces.md
```

Use lowercase kebab-case after the date. The date is the date of the record, not
the date of the facts inside it.

For durable reference assets that are not event records, use a stable name:

```text
assets/research/billing-provider-comparison.md
```

## Asset Body Shape

An asset explains why it exists, what evidence it contains, and what promotes
when it becomes durable.

Recommended shape:

```markdown
# 2026-07-07 Topic

Purpose: one sentence explaining why this record exists.

## Context

What question was being answered or what work was being recorded.

## Evidence

Raw findings, source notes, observations, logs, or links.

## Durable Conclusions

Facts promoted, or ready to promote, into live context.

## Open Questions

Unresolved questions. Do not let these masquerade as live doctrine.
```

## Promotion Rule

Promotion is a deliberate act:

1. Identify the durable fact inside the asset.
2. Find the owning live file under `context/`.
3. Move the conclusion there in present-tense form.
4. Keep the asset as evidence.
5. Do not keep two live copies.
6. Run `contextkit audit`.

The live file mentions the asset only when provenance matters. The live file
does not depend on the asset for everyday routing.

## Quality Bar

An asset is good when a future agent can tell:

- why the record exists;
- whether it is evidence, plan, research, or session history;
- which conclusions were promoted into live context;
- which questions remain unresolved;
- that no secret or live-only state was committed.
