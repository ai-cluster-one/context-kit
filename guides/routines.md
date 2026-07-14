# Routines Guide

Use this guide when writing repeatable procedures under `routines/`.

This guide is the operational rule source for ContextKit routines. It applies Convergent Operations, One Fact One Home, and Tool Truth, then routes applied models and tool contracts to their context or capability owners.

## When To Create A Routine

Create a routine when the same class of work repeats, order matters, idempotency or safety needs preserving, the work is host-neutral, and the procedure applies live doctrine or tool surfaces by role.

Do not create a routine for a single command, one-off plan, domain model, table of IDs, copied tool contract, or task queue.

## File Contract

Each routine is one Markdown file with front matter:

```yaml
---
name: routine-name
description: Specific one-line trigger and outcome.
---
```

The filename stem equals `name`.

## Body Contract

Open with trigger, scope boundary, and definition of done.

Include:

- expected inputs or substrate;
- ordered steps;
- idempotency guard;
- stop conditions;
- low-confidence path;
- expected final state;
- context or capability surfaces to load by role.

Exclude durable domain models, raw evidence, copied command contracts, secrets, connection values, and open work queues.

## Producers And Processors

A producer routine enumerates a source into work items. It states source, item grain, deduplication key, "already produced" test, handoff target, and processor.

A processor routine works one item. It states item shape, idempotency check, recipe, result, and refusal or escalation path.

## Relationship To Owners

Routines apply models; they do not own models. If a routine needs a state model, load the context owner. If it needs a tool, use the tool's help, doctor, or guide surface.

## Validation

```sh
contextkit build --target all
contextkit audit
```

Review the generated routine index. The description should be enough for the agent to decide when to load the routine.
