# Capabilities Guide

Use this guide when a ContextKit project has enabled external tools under `capabilities/`.

This guide is the operational rule source for ContextKit capability envelopes. It applies Tool Truth and Human Gates, then routes capability behavior to the capability tool's own surfaces.

## Boundary

ContextKit inserts capability awareness supplied by the capabilities manager. It does not turn capabilities into ContextKit doctrine or compose a parallel capability index.

ContextKit owns:

- discovery of the project envelope layer;
- invocation of `capabilities context --fragment`;
- unchanged placement of the returned block in generated runtime context;
- warnings that affect context generation.

The capabilities manager owns the project gate, its manager intro, enabled capability enumeration, installed snapshots, and rendering of project identifiers, connections, and references. Individual capability tools own their command contracts, readiness, credentials, state homes, schemas, releases, and internal authoring doctrine.

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

Exit 4 is policy, not a crash. It means the action is blocked by a project gate or read-only connection. Ask the user. Do not enable a capability, change a connection, or lift write permission by yourself.

## Project Envelopes

Files under `capabilities/<name>/` hold project-side, non-secret references where capability doctrine allows them. If an envelope contains durable project doctrine that is not capability-specific, promote it into `context/`. If it contains capability-general doctrine, move it to the capability owner.

## Quality Bar

The boundary is healthy when the manager-owned block says which capabilities are enabled, ContextKit inserts it without interpretation, detailed use is discovered from the capability, readiness is checked at use time, and ContextKit docs do not copy capability contracts.
