# ContextKit Authoring Guide

## Creating or editing context files

Put current project doctrine in `context/`. Every Markdown file must start with:

```yaml
---
title: Human title
description: Specific one-line routing description.
load: inline|stub
order: 100
---
```

Use `load: inline` only when the body is needed in nearly every run. Use
`load: stub` when the model only needs the title, path, and description until a
task calls for that doctrine.

## Ownership rules

- One durable fact has one live home.
- When adding a fact, identify the owning layer and file before writing.
- If a fact already exists elsewhere, update or move it instead of duplicating.
- Make `description` specific enough that the model can decide when to load it.
- Avoid Markdown links between context files as routing; generated metadata owns routing.
- Keep live state, worklists, pending balances, and open task scratch out of context.

## After authoring

Run `contextkit build --target all` and `contextkit audit`. If the audit points
to bloat, duplicate facts, weak descriptions, or wrong placement, fix the source
file and rebuild.
