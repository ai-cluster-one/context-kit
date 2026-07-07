# Operating Doctrine

Live doctrine: action rules, evidence routing, repeatable procedures, enabled
tool envelopes, host bindings.

Always-on: orientation, law, routing, safety.
On-demand: authoring guides, validation guides, audit guides, repair guides.

## Commands

- `contextkit doctor`: project shape and binding check. Rule sources:
  `contextkit guide validation`, `contextkit guide bootstrap`.
- `contextkit build --target all`: compile source body into host runtime
  context.
- `contextkit audit`: machine findings. Rule source: `contextkit guide audit`.
  Each finding names its own `rule_source`.
- `contextkit audit-file <path>`: machine findings for one file.
- `contextkit audit --write`: persisted report under `.contextkit/audits/`.
- `contextkit migrate --plan`: migration plan. Rule source:
  `contextkit guide migration`.
- `contextkit groom --plan`: repair plan from audit findings.

Flow: run command, load named rule source, edit source file, rerun command.
Repairs edit source files, never generated output.

## Laws

### One fact, one home

Every durable fact has one live home: principle, path, command, identifier,
workflow rule, limitation, or project decision.

Before adding a fact: find the owner. Update the owner. If no owner exists,
create one. Other surfaces route to the owner; they do not restate the fact.

Generated context, README prose, routines, assets, and host-specific files are
not parallel doctrine homes.

### Altitude

Always-on context: orientation, law, routing, safety.
Stub context: discoverable doctrine loaded by task.
Assets: evidence, history, research, plans, session records.
Routines: repeatable ordered work.
Capabilities: tool awareness and project envelopes.
Tool contracts, readiness, credentials, connections: owning tool or manager.

### Tool truth

Command-answerable knowledge lives in the command.

- ContextKit: `contextkit help`, `contextkit guide <topic>`,
  `contextkit doctor`, `contextkit audit`.
- Capabilities: `<capability> help`, `<capability> doctor`,
  `<capability> connections`, `<capability> guide <topic>`.

Do not transcribe CLI contracts, output schemas, readiness claims, or generated
indexes into prose. Prove readiness at use-time.

### Present tense

State what exists now. No "formerly", no migration story, no comparison as
definition. Change history lives in git, assets, or audit reports.

### Source edits

Edit source files. Do not edit generated files.
Prefer small auditable edits.

Generated files:

- `.codex/generated/context.md`
- `.claude/rules/CONTEXT.md`

### Human voice

Drafted human text preserves the user's voice and intent.

## Body Layers

### `.contextkit/`

Technical binding: config, manager marker, ContextKit-native artifacts,
`.contextkit/audits/`.

Not project body. No live project doctrine.

### `context/`

Live doctrine. Rule source for creation, movement, and audit:
`contextkit guide authoring`.

### `assets/`

Evidence and history. Rule source for records and promotion:
`contextkit guide assets`.

ContextKit audit reports: `.contextkit/audits/`.

### `routines/`

Repeatable procedures. Rule source: `contextkit guide routines`.

### `capabilities/`

Enabled tool envelopes. ContextKit indexes awareness only. Rule source for the
ContextKit boundary: `contextkit guide capabilities`. Capability internals:
capabilities manager and capability-owned guides.

## Rule Sources

- `contextkit guide bootstrap`: new project body, adoption, required files.
- `contextkit guide authoring`: `context/` files, live doctrine placement.
- `contextkit guide validation`: validation sequence and checks.
- `contextkit guide audit`: audit walk, finding classes, report shape.
- `contextkit guide assets`: evidence records and promotion.
- `contextkit guide routines`: repeatable procedures.
- `contextkit guide capabilities`: ContextKit/capability boundary.
- `contextkit guide destructive`: destructive or state-erasing operations.
- `contextkit guide migration`: legacy and mixed-layout migration.
- `contextkit guide hooks`: host bindings and generated context delivery.

## Work Loop

Before editing: identify owner, search existing owner.

After editing live context, routines, hooks, or capability envelopes:

```sh
contextkit doctor
contextkit build --target all
contextkit audit
```
