# ContextKit Operating Doctrine

This is the live doctrine that explains how to act, the supporting evidence, the
repeatable procedures, the enabled tool envelopes, and the host bindings that
compile all of that into runtime context.

Always-on context stays compact: orientation, law, routing, safety. Detailed
authoring and repair mechanics live in on-demand guides.

## Mechanism Model

Verbs run mechanisms. Guides hold rules.

`contextkit audit`, `contextkit groom`, `contextkit migrate`, and
`contextkit build` produce mechanical output. The output names rule sources.
Rule sources are guides. Repairs change source files, never generated output.

Flow:

1. Run the verb.
2. Load the named rule-source guide.
3. Apply the guide to the source file or layer.
4. Rerun the verb.

## Operating Constitution

### One fact, one home

Every durable fact has exactly one live home: a principle, a path, a command, an
identifier, a workflow rule, a limitation, or a project decision. A second copy
is already drift waiting to happen. Before adding a fact, find whether it
already has an owner; update that owner or point to it by role.

Generated context, README prose, routines, assets, and host-specific files must
not restate live doctrine unless they are the owner. They may route to the owner.

### Lean by altitude

Always-on context carries only what every session needs to navigate: what exists,
what owns what, what must never be violated, and when to load deeper material.
Operational detail waits in the layer that owns it.

Use this altitude test before writing:

- Needed in nearly every session to stay oriented or safe: live inline context.
- Needed only for a class of work: stub context or an on-demand guide.
- Historical, evidential, or exploratory: `assets/`.
- Ordered repeatable work: `routines/`.
- Tool contract, readiness, credentials, or connection behavior: the capability
  or manager that owns that tool.

### Discoverable Knowledge Lives in the Tool

If a command can answer a question, the command is the source of truth. Use
`contextkit help`, `contextkit guide <topic>`, `contextkit doctor`, and
`contextkit audit` for ContextKit. Use `<capability> help`, `<capability>
doctor`, `<capability> connections`, and `<capability> guide <topic>` for
capabilities.

Do not transcribe CLI contracts, output schemas, readiness claims, or generated
indexes into prose that will drift. Readiness is proven at use-time.

### Affirmative and Present

State what a thing is, now. Avoid defining a file by what it replaced, what it is
not, or what a neighboring system does. Change history lives in git and audit
reports. A justified exception is recorded where it belongs; it is not smuggled
as vague defensive prose.

### Agent Work Is Accountable

Work from source files, not generated files. Keep the user looped in when a
change affects structure, doctrine, safety, or external systems. Prefer a small,
auditable edit over a broad rewrite unless the body itself needs reshaping.

When drafting text on the user's behalf, preserve the user's voice and intent.
Do not turn human communication into generic assistant prose.

## Project Body Layers

### `.contextkit/`

`.contextkit/` is the technical binding: config, manager marker, and ContextKit
native artifacts such as `.contextkit/audits/`. It is not the project body and
does not hold live project doctrine.

### `context/`

`context/` is the live source of truth for current project doctrine. Load
`contextkit guide authoring` before creating, moving, or judging context files.

### `assets/`

`assets/` holds supporting evidence and historical material. Load
`contextkit guide assets` before creating, judging, or promoting asset content.
ContextKit's own written audit reports live under `.contextkit/audits/`.

### `routines/`

`routines/` holds repeatable procedures. Load `contextkit guide routines` before
creating, judging, or repairing routines.

### `capabilities/`

`capabilities/` is the project envelope layer for enabled external tools.
ContextKit indexes enabled capability awareness into generated context. Load
`contextkit guide capabilities` for the ContextKit boundary, then use the
capabilities manager or capability-owned guide for capability internals.

## On-Demand Guides

Load a guide when its trigger applies:

- `contextkit guide bootstrap` - creating a new project body or adopting an
  existing repo.
- `contextkit guide authoring` - creating or editing `context/`, `assets/`,
  `routines/`, or any agent-directing Markdown.
- `contextkit guide validation` - checking whether a project body is coherent
  before committing or after migration.
- `contextkit guide audit` - judging existing context and planning repairs.
- `contextkit guide assets` - deciding whether material belongs in `assets/` or
  promotes into live doctrine.
- `contextkit guide routines` - creating or revising repeatable procedures.
- `contextkit guide capabilities` - understanding the ContextKit/capability
  boundary.
- `contextkit guide destructive` - before a database-destructive or
  state-erasing operation.
- `contextkit guide migration` - converting legacy or mixed project layouts.
- `contextkit guide hooks` - changing Codex, Claude, or other host bindings.

## Daily Working Loop

Before editing, identify the owning layer and search for an existing home. After
editing live context or procedures, run:

```sh
contextkit doctor
contextkit build --target all
contextkit audit
```

Use `contextkit audit-file <path>` for one file and `contextkit audit --write`
for a persisted report under `.contextkit/audits/`.

Generated files such as `.codex/generated/context.md` and
`.claude/rules/CONTEXT.md` are build artifacts. Do not edit them by hand.
