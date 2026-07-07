# Capabilities Guide

Use this guide when deciding what ContextKit owns about capabilities and what it
must leave to the capabilities manager/repo.

Capabilities are external tools. ContextKit does not turn them into ContextKit
doctrine. ContextKit only surfaces the enabled capability set as one layer of the
agent body.

## What ContextKit Owns

ContextKit owns:

- discovering the project envelope layer at `capabilities/`;
- reading `capabilities/settings.json` as the project gate;
- indexing enabled capability awareness into generated runtime context;
- surfacing installed capability stubs and guide topic names when available;
- warning when the capability layer is absent or malformed enough to affect
  context generation.

ContextKit's generated context tells the agent that capability CLIs are available
on PATH and that each tool's own surface is authoritative.

## What ContextKit Does Not Own

ContextKit does not define:

- how to create a capability;
- how to validate or audit a capability implementation;
- capability release or install mechanics;
- credential cascade rules;
- connection registries;
- capability state homes;
- command contracts, schemas, or output envelopes;
- capability-specific authoring guides.

Those belong to the capabilities manager and the capability repo. If a fact is
about the internal design of a capability, it does not belong in ContextKit.

## Operating A Capability

Use the tool's own surface:

```sh
<name> help
<name> doctor
<name> connections
<name> guide <topic>
```

Use the manager for the installed/enabled set:

```sh
capabilities list
capabilities enable <name>
capabilities disable <name>
capabilities update <name>
```

Readiness is proven by `<name> doctor`, not by a prose claim in context.

## Policy Gates

Exit 4 is policy, not a crash. It means the action is blocked by a project gate
or a read-only connection. The agent should ask the user and should not enable a
capability, change a connection, or lift write permission by itself.

## Project Envelopes

Files under `capabilities/<name>/` are project-side envelopes for that tool:
non-secret identifiers, references, connection declarations, and state guards
where the capability doctrine allows them. ContextKit may list their presence,
but it does not reinterpret their internal meaning.

If an envelope contains durable project doctrine that is not capability-specific,
promote that fact into `context/`. If it contains capability authoring doctrine,
move it to the capability repo.

## Quality Bar

The ContextKit/capability boundary is healthy when:

- generated context tells the agent which capabilities are enabled;
- detailed use is discovered through the capability CLI;
- readiness is checked at use-time;
- project-specific capability references stay in the project envelope;
- capability-general doctrine stays in the capability repo;
- ContextKit docs do not copy capability contracts.
