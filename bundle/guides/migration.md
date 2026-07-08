# Migration Guide

Migration converts existing projects into ContextKit agent bodies, especially
repos with legacy dot body folders, host-specific instruction files, or scattered
project memory.

Migration starts with classification, then file moves. Layer guides contain the
destination rules.

## Start With A Plan

```sh
contextkit migrate --plan
```

Read the plan before changing files. It reports visible layers, bootstrap files,
host bindings, and instruction files that may overlap with generated ContextKit
output.

## Classification Pass

For each existing file or paragraph, choose the destination by loading the guide
that owns the candidate layer:

| Candidate destination | Rule source |
| --- | --- |
| `context/` | `contextkit guide authoring` |
| `assets/` | `contextkit guide assets` |
| `routines/` | `contextkit guide routines` |
| `capabilities/` | `contextkit guide capabilities`, then capability-owned docs |
| generated host output | `contextkit guide hooks` |
| local secrets/config | `contextkit guide bootstrap` and the owning tool docs |

If a fact appears in several places, pick the owner and remove the rest or turn
them into role pointers according to the owning guide.

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
valuable doctrine. They do not remain a second source of truth once ContextKit
owns generated runtime context.

Classify their content with the guide routing table above. Then let ContextKit
generate host context.

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
