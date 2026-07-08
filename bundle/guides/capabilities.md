# Capabilities Guide

Use this guide when a ContextKit project has enabled external tools under
`capabilities/`.

Rule owners: Tool Truth, Human Gates, Capabilities Standard, and the capability
tool's own surfaces.

## Boundary

ContextKit indexes capability awareness. It does not turn capabilities into
ContextKit doctrine.

ContextKit owns:

- discovery of the project envelope layer;
- the project gate in `capabilities/settings.json`;
- enabled capability awareness in generated runtime context;
- installed stubs and guide topic names when available;
- warnings that affect context generation.

Capability tools own their command contracts, readiness, credentials,
connections, state homes, schemas, releases, and internal authoring doctrine.

## Operating A Capability

Use the tool's own live surfaces:

```sh
<name> help
<name> doctor
<name> connections
<name> guide <topic>
```

Use the capabilities manager for the installed/enabled set.

Readiness is proven by the capability's doctor surface, not by prose in context.

## Policy Gates

Exit 4 is policy, not a crash. It means the action is blocked by a project gate
or read-only connection. Ask the user. Do not enable a capability, change a
connection, or lift write permission by yourself.

## Project Envelopes

Files under `capabilities/<name>/` hold project-side, non-secret references
where capability doctrine allows them. If an envelope contains durable project
doctrine that is not capability-specific, promote it into `context/`. If it
contains capability-general doctrine, move it to the capability owner.

## Quality Bar

The boundary is healthy when generated context says which capabilities are
enabled, detailed use is discovered from the capability, readiness is checked at
use time, and ContextKit docs do not copy capability contracts.
