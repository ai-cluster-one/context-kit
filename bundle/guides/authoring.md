# ContextKit Authoring Guide

Use this guide when creating, moving, or repairing project body material.

Rule owners: Context Lens, Altitude, One Fact One Home, Present-Tense Doctrine,
Machine-Readable Context, Context Files Standard, Assets Standard, Routines
Standard, Capabilities Standard, and Generated Output Standard.

## Placement

Classify the material before writing:

- current law, identity, architecture, constraints, or stable project model:
  `context/`;
- historical evidence, research, plans, raw notes, session records, or
  snapshots: `assets/`;
- repeatable ordered work: `routines/`;
- enabled tool envelopes, identifiers, connection declarations, and
  project-specific capability references: `capabilities/`;
- ContextKit-native reports: `.contextkit/`;
- generated host context: never edit by hand.

Placement tests:

- true for future sessions: live doctrine;
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

Use `load: inline` only for compact material needed in nearly every session to
keep the agent safe, oriented, or aligned. Use `load: stub` for detailed
doctrine loaded by task.

Default homes:

- `context/identity/` - mission, roles, owner identity, people, entities, and
  stable responsibilities;
- `context/guidelines/` - laws, constraints, limits, decision rules, safety
  boundaries, and quality bars;
- `context/architecture/` - runtime shape, services, data flow, deployment,
  integrations, and host surfaces.

Create a domain folder only when the domain earns a stable shelf. Name files for
the durable domain they own, not for the task that created them. Do not encode
dates in live context filenames.

## Body Rules

Open with what the file owns and where its boundary ends. State current doctrine
in present tense.

Keep:

- durable facts stated affirmatively;
- one fact in one home;
- reader-appropriate voice;
- routing to neighboring owners only when necessary.

Exclude:

- task state, balances, checkpoints, or open queues;
- migration history and internal arguments;
- copied command contracts, schemas, readiness claims, or generated output;
- asset paths used as live doctrine;
- secrets or local machine values.

## Authoring Procedure

1. State the fact or procedure in one sentence.
2. Search for an existing owner with `rg`.
3. Choose the layer: `context/`, `assets/`, `routines/`, `capabilities/`, or
   `.contextkit/`.
4. Load the guide that owns that layer.
5. Write only what the selected file owns.
6. Remove or rewrite duplicates instead of adding a parallel truth.
7. Run validation.

```sh
contextkit doctor
contextkit build --target all
contextkit audit
```

## Quality Bar

A new or edited body file is good when future agents can tell when to load it,
what it owns, what it excludes, and how to validate the change.
