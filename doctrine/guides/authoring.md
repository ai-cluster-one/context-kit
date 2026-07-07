# ContextKit Authoring Guide

Live context authoring under `context/`; project-body owner selection for
durable facts; agent-directing Markdown placement.

Durable knowledge has one correct home, at the correct altitude, with enough
routing metadata for generated context to find it.

## The Placement Decision

Before writing, classify the material:

- **Current law, identity, architecture, constraints, or stable project model**:
  write it under `context/`.
- **Repeatable ordered work**: write it under `routines/`, then load
  `contextkit guide routines`.
- **Historical evidence, research, plans, raw notes, session records, or
  snapshots**: write it under `assets/`, then load `contextkit guide assets`.
- **Enabled tool envelopes, identifiers, connection metadata, and capability
  references**: keep them under `capabilities/`, following the capability
  manager's own doctrine; load `contextkit guide capabilities` for the
  ContextKit boundary.
- **ContextKit native reports**: keep them under `.contextkit/`, especially
  `.contextkit/audits/`.
- **Generated host context**: never write it by hand.

Placement test:

- True for future sessions: live doctrine.
- Evidence for a past conclusion: asset.
- Recurring ordered work: routine.

## `context/` Taxonomy

`context/` holds live doctrine. Start with the default folders, then add a new
folder only when a real domain needs its own shelf.

Use these default homes:

- `context/identity/` - mission, agent role, owner identity, people, entities,
  stable responsibilities.
- `context/guidelines/` - project laws, constraints, limitations, decision
  rules, safety boundaries, quality bars.
- `context/architecture/` - runtime shape, services, data flow, deployment
  model, integration boundaries, host surfaces.

Add domain folders only when the default homes become muddy. Examples:
`context/product/`, `context/accounting/`, `context/operations/`,
`context/editorial/`. A folder name is the domain, not the current task.

Do not create a folder for one orphan note. Put the note in the nearest existing
home; split later when the shape earns it.

## Context File Contract

Every context file is Markdown with YAML front matter:

```yaml
---
title: Human title
description: Specific one-line routing description.
load: inline|stub
order: 100
---
```

Fields:

- `title`: human-readable label used in generated context.
- `description`: one line that answers "when the agent loads this file."
  It is routing metadata, not a subtitle.
- `load`: `inline` or `stub`.
- `order`: numeric sorting key. Files sort by `order`, then path.

Do not add extra front matter fields unless ContextKit learns to use them. Extra
metadata becomes invisible ceremony.

## Description Quality

A weak description says what the file is called. A strong description says when
the agent needs it.

Weak:

```yaml
description: Project context and details.
```

Strong:

```yaml
description: Load when changing billing behavior, invoice states, or payment reconciliation rules.
```

Description rules:

- Make it specific to the decision surface.
- Keep it one line.
- Name triggers and scope boundaries.
- Avoid generic words like "notes", "misc", "information", "details", "context".
- Do not use the description to summarize every fact in the file.

## Load Mode

Use `load: inline` only when the body is needed in nearly every session to keep
the agent safe, oriented, or aligned. Inline context is paid for every time.

Good inline candidates:

- project mission or identity that changes how every task is interpreted;
- compact constitutional rules;
- critical constraints that prevent dangerous work;
- runtime rules that all host bindings must obey.

Use `load: stub` for everything else. A stub file is still discoverable in
generated context by title, path, and description. The agent loads it on demand.

Good stub candidates:

- detailed architecture;
- service maps;
- domain models;
- people/entity directories;
- workflow policies used only for a class of work;
- long limitations or decision trees.

If an inline file grows past the point where most sessions need every paragraph,
split it: keep the law inline and move examples, tables, and rare detail into a
stub file.

## Naming

Name files for the stable domain they own, not for the task that created them.

For canonical, small, standing doctrine in the default folders, prefer clear
uppercase names:

```text
context/identity/MISSION.md
context/guidelines/CONSTITUTION.md
context/architecture/RUNTIME.md
```

For a folder that will contain many peer files, use lowercase kebab-case:

```text
context/product/pricing-model.md
context/operations/month-end-close.md
context/integrations/payment-provider.md
```

Pick one style inside a folder and keep it coherent. Do not encode dates in live
context filenames; dates are for assets and audit reports.

## Body Contract

Open with the scope: what this file owns and where its boundary ends. Then state
the current doctrine in present tense.

A good context body:

- states durable facts affirmatively;
- keeps one fact in one home;
- names other homes by role only when routing is necessary;
- avoids change history, migration notes, and "formerly";
- avoids long copied command contracts or generated output;
- promotes conclusions from assets without rewriting the evidence;
- separates law from procedure.

Exclude from context bodies:

- store open task lists, balances, checkpoints, or session state;
- point at `assets/` as if assets are live doctrine;
- duplicate capability help, schemas, credential rules, or readiness checks;
- rely on Markdown links between sibling context files for routing;
- defend itself with noisy self-validation prose.

## Templates

Inline constitutional file:

```markdown
---
title: Project Constitution
description: Always load for project-wide laws, safety boundaries, and doctrine ownership rules.
load: inline
order: 100
---

# Project Constitution

This file owns the project-wide laws that every session must preserve.

## Law Name

State the law in present tense. Say what must hold and why it matters. Put
procedure, examples, and rare edge cases in a stub or routine.
```

Stub architecture file:

```markdown
---
title: Service Runtime
description: Load when changing service boundaries, deployment shape, queues, workers, or runtime ownership.
load: stub
order: 220
---

# Service Runtime

This file owns the current runtime shape of the project.

## Services

State the live service model and boundaries.

## Data Flow

State durable flow facts. Keep provider API contracts in the provider capability
or official docs.
```

Stub domain model:

```markdown
---
title: Invoice Domain Model
description: Load when changing invoice states, billing transitions, or reconciliation behavior.
load: stub
order: 320
---

# Invoice Domain Model

This file owns the live billing-domain vocabulary and state model.

## States

State the current model. Do not include historical migrations or raw research.
```

For routine templates, load `contextkit guide routines`. For asset templates,
load `contextkit guide assets`. This guide routes to those homes but does not
own their file contracts.

## Authoring Procedure

1. State the fact or procedure in one sentence.
2. Search the project for an existing owner with `rg`.
3. Choose the layer: `context/`, `assets/`, `routines/`, `capabilities/`, or
   `.contextkit/`.
4. Load the guide that owns that layer.
5. If writing `context/`, choose folder, filename, `load`, and `order`.
6. Write only the facts this file owns.
7. Remove or rewrite duplicates instead of adding a parallel truth.
8. Run `contextkit build --target all`.
9. Run `contextkit audit` or `contextkit audit-file <path>`.

## Quality Bar

A new or edited file is good when:

- a future agent can tell from generated context when to load it;
- the file owns a clear domain and does not leak into neighboring domains;
- every durable fact has one home;
- always-on text is small enough to justify its per-session cost;
- asset, routine, and capability details were judged by their owning guides;
- `contextkit audit` is clean or every remaining warning is deliberate.
