# Routines Guide

Use this guide when creating or revising repeatable work under `routines/`.

A routine is a procedure the agent should run more than once. It is earned when
the work has a stable trigger, a stable outcome, and enough sequencing that
re-deriving it each time creates waste or risk.

## When To Create A Routine

Create a routine when:

- the same class of work repeats;
- the order of steps matters;
- there is an idempotency or safety boundary to preserve;
- the work can be described without depending on one host;
- the procedure applies live doctrine or capability surfaces by role.

Do not create a routine for:

- a single command;
- a one-off plan;
- a domain model;
- a table of ids;
- capability help or contract details;
- task state that belongs in a work tracker.

## File Contract

Each routine is one Markdown file under `routines/` with front matter:

```yaml
---
name: routine-name
description: Specific one-line trigger and outcome.
---
```

The filename stem should match `name`:

```text
routines/month-end-close.md
routines/release-check.md
routines/processor/invoice.md
```

Descriptions are routing surfaces. A good description says when to run the
routine and what outcome it produces.

Weak:

```yaml
description: Steps for invoices.
```

Strong:

```yaml
description: Run when processing one invoice through validation, posting, and reconciliation.
```

## Naming And Grouping

Prefer one routine per stable trigger/outcome pair.

Common grouping:

- `routines/producer/` - enumerates source material into jobs.
- `routines/processor/` - works one job or item.
- top-level `routines/*.md` - ordinary project procedures.

Use singular nouns for processors (`invoice.md`, `lead.md`) and verb-object or
domain names for ordinary procedures (`release-check.md`, `month-end-close.md`).

## Body Contract

Open with the trigger, the scope boundary, and the definition of done.

A routine should include:

- when to run it;
- inputs or substrate it expects;
- ordered steps;
- idempotency guard;
- stop conditions;
- what to do when confidence is low;
- expected final state;
- which context or capability surfaces to load by role.

A routine should not include:

- durable domain models that belong in `context/`;
- raw evidence that belongs in `assets/`;
- copied capability command surfaces;
- secrets, credentials, or connection values;
- project work queues or open task lists.

## Producers And Processors

A producer routine enumerates a source into work items. It states:

- source to inspect;
- grain of one produced item;
- deduplication key;
- how "already produced" is determined;
- where the item is handed off;
- which processor handles it.

A processor routine works one item. It states:

- item shape or substrate;
- idempotency check;
- recipe;
- result;
- refusal/escalation path when the item cannot be handled safely.

The processor should not know more about the producer than necessary. It works
the item it was given.

## Relationship To Context And Capabilities

Routines apply models; they do not own models. If a routine needs a billing
state model, it names the billing context file by role and loads it. If it needs
a tool, it calls the capability's own help/doctor/guide surface.

Do not copy identifiers, mappings, API payloads, or command contracts into a
routine. Those belong in the owning context file, capability envelope, or tool.

## Validation

After editing routines:

```sh
contextkit build --target all
contextkit audit
```

Then review the generated routine index. The description should be enough for an
agent to decide when to load the routine.
