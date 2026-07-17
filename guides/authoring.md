# ContextKit Authoring Guide

Use this guide when creating, moving, or repairing project body material.

This guide is the operational rule source for project-body authoring. It applies Context Lens, Altitude, One Fact One Home, Present-Tense Doctrine, Machine-Readable Context, Direct Address, Semantic Line Breaks, and Generated Output, then routes layer-specific work to the memory, assets, routines, and capabilities guides.

## Placement

Classify the material before writing:

- current law, identity, architecture, constraints, or stable project model: `context/`;
- live doctrine shared unchanged by multiple projects: the configured global context source after loading `contextkit guide global-context`;
- provisional project knowledge that future sessions must account for before it has a durable owner: the active project memory root after loading `contextkit guide memory`;
- historical evidence, research, plans, raw notes, session records, or snapshots: `assets/`;
- repeatable ordered work: `routines/`;
- enabled tool envelopes, identifiers, connection declarations, and project-specific capability references: `capabilities/`;
- ContextKit-native reports: `.contextkit/`;
- generated host context: never edit by hand.

Placement tests:

- settled and true for future sessions: live doctrine;
- needed by future sessions but not yet settled: project memory;
- evidence for a past conclusion: asset;
- recurring ordered work: routine;
- command-answerable fact: owning tool or CLI.

## Context Files

Each `context/**/*.md` file has front matter:

```yaml
---
title: Human title
description: Specific one-line routing description.
load: inline|stub
order: 100
---
```

Use `load: inline` only for compact material needed in nearly every session to keep the agent safe, oriented, or aligned. Use `load: stub` for detailed doctrine loaded by task.

Default homes:

- `context/identity/` - mission, roles, owner identity, people, entities, and stable responsibilities;
- `context/guidelines/` - laws, constraints, limits, decision rules, safety boundaries, and quality bars;
- `context/architecture/` - runtime shape, services, data flow, deployment, integrations, and host surfaces.

Create a domain folder only when the domain earns a stable shelf. Name files for the durable domain they own, not for the task that created them. Do not encode dates in live context filenames.

## Body Rules

Open with what the file owns and where its boundary ends. State current doctrine in present tense.

Address the active agent directly as `you` when defining its identity, authority, boundaries, or behavior. Use imperatives for actions, third person for project and external facts, and impersonal language for universal laws. Avoid first person unless the artifact explicitly owns a speaker.

Write each prose paragraph and list item on one physical line. Do not hard-wrap at a column width; use line breaks only when they encode Markdown structure.

Keep:

- durable facts stated affirmatively;
- one fact in one home;
- reader-appropriate voice;
- semantic routing to neighboring owners by the capability, procedure, or knowledge needed.

Exclude:

- task state, balances, checkpoints, or open queues;
- migration history and internal arguments;
- copied command contracts, schemas, readiness claims, or generated output;
- asset paths used as live doctrine;
- secrets or local machine values.

## Semantic Routing

Keep authored project-body files independent of sibling paths. Do not link to another project-body file or restate its contents to make the current file work. Express the capability, procedure, or knowledge the agent needs in domain terms and let compiled descriptions and live discovery identify an available owner at use time.

Do not name a particular routine, capability, or file merely because it exists while authoring. A routine can be removed and a capability can be disabled. When work requires an optional owner, tell the agent how to discover an available owner and define the fallback, stop condition, or escalation path when discovery finds none. Do not infer that a missing owner exists or invent its behavior.

Name a guide, tool, or configuration anchor when that named surface is itself the durable owner or discovery mechanism. Use the owner's live help, doctor, guide, or index instead of copying its contract into project-body prose.

## Authoring Procedure

1. State the fact or procedure in one sentence.
2. Search for an existing owner with `rg`.
3. Choose the layer: project `context/`, configured global context, `assets/`, `routines/`, `capabilities/`, or `.contextkit/`.
4. Load the guide that owns that layer.
5. Write only what the selected file owns.
6. Express dependencies semantically and define the no-owner path.
7. Remove or rewrite duplicates instead of adding a parallel truth.
8. Run validation.

```sh
contextkit doctor
contextkit build --target all
contextkit audit
```

## Quality Bar

A new or edited body file is good when future agents can tell when to load it, what it owns, what it excludes, and how to validate the change.
