# Audit Guide

Use audits to judge whether the project body is coherent: every fact has one
home, the live layer is current, always-on context is lean, and the generated
runtime context can route an agent reliably.

Commands:

```sh
contextkit audit
contextkit audit-file context/path/to/file.md
contextkit audit --write
```

`contextkit audit` is advisory by default. `contextkit audit --write` persists a
dated report under `.contextkit/audits/`.

## What The Audit Is Judging

The audit is not checking whether the prose is pretty. It is judging whether the
agent body can be trusted.

Primary questions:

- Can an agent tell what exists and when to load it?
- Is each durable fact stated in exactly one live home?
- Does every context file own a clear domain?
- Is always-on context small enough to justify its cost?
- Are assets treated as evidence rather than hidden doctrine?
- Are routines procedural rather than duplicating models?
- Are capability details left to the capability layer?
- Are generated files left untouched?

## Severity Model

Treat findings in this order:

1. **Errors** - metadata or structure that blocks compilation or routing.
2. **Warnings** - likely drift, duplication, weak routing, wrong altitude, or
   unsafe placement.
3. **Info** - taxonomy or quality hints that deserve human judgment.

A quiet audit is not the goal by itself. A coherent body is the goal. If a
warning is deliberately accepted, record the reason where the exception lives.

## Manual Audit Pass

Use this pass when migrating a repo or reviewing a large context change:

1. Run `contextkit doctor`.
2. Run `contextkit build --target all`.
3. Run `contextkit audit --write`.
4. Read the generated report in `.contextkit/audits/`.
5. For every finding, identify the owner file before editing.
6. Fix metadata and load-mode errors first.
7. Merge duplicate durable facts into one home.
8. Move procedural material into `routines/`.
9. Move historical material into `assets/` and promote only durable conclusions.
10. Rebuild and audit again.

## File-Level Audit

Use `contextkit audit-file <path>` while authoring one file. A file passes review
when:

- its front matter is valid;
- its description is specific enough to route loading;
- its `load` mode matches its body size and frequency;
- it states current facts, not history;
- it does not point to assets as live doctrine;
- it does not duplicate sibling context;
- it does not contain task state, todos, or operational scratch.

## Repair Patterns

Weak description:

```yaml
description: Billing information.
```

Repair:

```yaml
description: Load when changing billing states, invoice rules, or payment reconciliation behavior.
```

Duplicate live fact:

- Pick the owning domain.
- Move the full fact there.
- Replace other copies with a short role pointer only if routing requires it.

Inline bloat:

- Keep the universal law inline.
- Move examples, tables, rare cases, and long explanations into a stub file.

Asset as doctrine:

- Promote the current conclusion to `context/`.
- Leave the historical record in `assets/`.
- Remove language that tells the agent to treat the asset as the live authority.

Capability bleed:

- Replace copied command details with `<capability> help`.
- Replace copied readiness claims with `<capability> doctor`.
- Replace copied authoring doctrine with `<capability> guide <topic>`.

## Before Commit

Before committing a body change:

```sh
contextkit doctor
contextkit build --target all
contextkit audit
git status --short
```

Confirm that generated files such as `.codex/generated/context.md` and
`.claude/rules/CONTEXT.md` are not staged unless the project intentionally tracks
generated output.
