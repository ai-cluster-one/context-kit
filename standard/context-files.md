# Context Files Standard

Rule source for authored Markdown files under a project's `context/` layer.

## Front Matter Contract

Every context file is Markdown with YAML front matter:

```yaml
---
title: Human title
description: Specific one-line routing description.
load: inline|stub
order: 100
---
```

`title` is the generated label. `description` says when the agent should load
the file. `load` is `inline` or `stub`. `order` sorts files numerically, then by
path.

## Placement

Use default homes first:

- `context/identity/` for mission, role, owner identity, people, entities, and
  stable responsibilities;
- `context/guidelines/` for laws, constraints, limits, decisions, safety
  boundaries, and quality bars;
- `context/architecture/` for runtime shape, services, data flow, deployment,
  integration boundaries, and host surfaces.

Create domain folders only when the domain earns a stable shelf.

## Load Modes

Use `inline` only for compact material needed in nearly every session to keep
the agent safe, oriented, or aligned. Use `stub` for detailed doctrine loaded by
task.

## Body Contract

Open with what the file owns and where its boundary ends. State current doctrine
in present tense. Keep one durable fact in one home. Name other homes by role
only when routing is necessary.

Exclude task state, copied command contracts, generated output, secret values,
historical arguments, and asset paths used as live doctrine.

## Quality Bar

A context file is good when a future agent can tell when to load it, what it
owns, what it excludes, and which source owns neighboring facts.
