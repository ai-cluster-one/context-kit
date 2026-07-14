# Migration Guide

Use this guide when converting an existing project into a ContextKit agent body.

This guide is the operational rule source for migration. It applies Visible Body, Bounded Compatibility, Project Stewardship, One Fact One Home, and Generated Output, then routes moved material to the destination layer guide.

## Start With A Plan

```sh
contextkit migrate --plan
```

Read the plan before changing files. It reports visible layers, bootstrap files, host bindings, generated targets, and instruction files that may overlap with ContextKit output.

## Classification

For each existing file or paragraph, choose the destination by loading the owner for that destination:

| Destination             | Rule source                                                     |
| ----------------------- | --------------------------------------------------------------- |
| `context/`              | `contextkit guide authoring`                                    |
| `assets/`               | `contextkit guide assets`                                       |
| `routines/`             | `contextkit guide routines`                                     |
| `capabilities/`         | `contextkit guide capabilities`, then capability-owned surfaces |
| generated host output   | `contextkit guide hooks`                                        |
| local secrets or config | `contextkit guide bootstrap` and the owning tool                |

If a fact appears in several places, pick the owner and remove the rest or turn them into role pointers.

## Legacy Dot Folders

Visible body folders are canonical:

```text
context/
assets/
routines/
capabilities/
```

Dot folders are migration inputs:

```text
.context/       -> context/
.assets/        -> assets/
.routines/      -> routines/
.capabilities/  -> capabilities/
```

Use `git mv` when possible. Merge collisions manually. Preserve evidence and current doctrine instead of overwriting.

## Host Instruction Files

Root instruction files such as `CLAUDE.md` or `AGENTS.md` may contain valuable doctrine. They do not remain a second source of truth once ContextKit owns generated runtime context. Classify their contents, move durable facts to the owner, and let ContextKit generate host context.

## Verification

```sh
contextkit doctor
contextkit build --target all
contextkit audit --write
```

Migration is complete when generated context has equal or better routing value than the old host-specific files without duplicating their facts.
