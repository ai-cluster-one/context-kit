# Migration Guide

Use this guide when converting an existing project, especially one with legacy
dot body folders, host-specific instruction files, or scattered project memory.

Migration is a classification exercise before it is a file move. Preserve
evidence, promote durable facts, and remove duplicated live truth.

## Start With A Plan

```sh
contextkit migrate --plan
```

Read the plan before changing files. It reports visible layers, bootstrap files,
host bindings, and instruction files that may overlap with generated ContextKit
output.

## Classification Pass

For each existing file or paragraph, choose one home:

- current durable doctrine -> `context/`;
- historical evidence, notes, plans, research -> `assets/`;
- repeatable ordered procedure -> `routines/`;
- project-side tool envelope -> `capabilities/`;
- generated host output -> delete/regenerate, do not preserve as source;
- secrets/local configuration -> local env or credential store, not git.

If a fact appears in several places, pick the owner and remove the rest or turn
them into role pointers.

## Legacy Dot Folders

Visible body folders are canonical:

```text
context/
assets/
routines/
capabilities/
```

Dot body folders are migration inputs:

```text
.context/       -> context/
.assets/        -> assets/
.routines/      -> routines/
.capabilities/  -> capabilities/
```

Use `git mv` when possible. Merge collisions manually; do not overwrite the
project's evidence or current doctrine.

## Host Instruction Files

Root files like `CLAUDE.md`, `AGENTS.md`, or hand-authored rules may contain
valuable doctrine, but they should not remain a second source of truth once
ContextKit owns generated runtime context.

Move durable content into `context/`, procedures into `routines/`, and evidence
into `assets/`. Then let ContextKit generate host context.

## Verification

After migration:

```sh
contextkit doctor
contextkit build --target all
contextkit audit --write
```

Review the report under `.contextkit/audits/`, fix the source files, rebuild, and
audit again.

Migration is complete when generated context has the same or better routing
value than the old host-specific files, without duplicating their facts.
