# ContextKit

ContextKit is a standalone manager for repo-backed agent project bodies. It
standardizes the visible project structure, durable context, runtime context
compilation, host bindings, routines, capabilities, audits, and migrations that
make an agent operable from a repository.

ContextKit is deliberately higher-rank than a normal capability. Capabilities
remain separate tools; ContextKit discovers and indexes them as one layer of the
agent body.

## What It Manages

An agent body is the repository shape that lets an agent operate consistently
across workers and hosts:

- `context/` - live doctrine and routing surface;
- `assets/` - historical evidence, plans, audits, research, and supporting
  material;
- `routines/` - repeatable procedures surfaced into runtime context;
- `capabilities/` - project envelopes for installed tools;
- `.contextkit/` - the technical binding, config, and manager-facing marker;
- `.codex/` and `.claude/` outputs/hooks - generated host runtime context.

## Install

```sh
curl -fsSL https://raw.githubusercontent.com/ai-cluster-one/context-kit/main/install.sh | sh
```

For local development, run the checked-out script directly:

```sh
./bin/contextkit help
```

## Core Commands

```sh
contextkit init
contextkit adopt
contextkit migrate --plan
contextkit install-hooks --target codex --target claude
contextkit build --target all
contextkit doctor
contextkit audit
contextkit audit --write
contextkit guide bootstrap
contextkit guide authoring
```

Use `contextkit init` for a new agent project. Use `contextkit migrate --plan`
and `contextkit adopt` for an existing repository; adopt adds the technical
binding and bootstrap files without creating body folders over legacy material.
Run `contextkit guide bootstrap` for the exact new-project and migration
sequences, including how Codex and Claude receive generated context.

## Project Shape

```text
.contextkit/
  README.md
  config.toml
.gitignore
.env.local
context/
  identity/
  guidelines/
  architecture/
assets/
  audits/
  sessions/
  plans/
  research/
routines/
capabilities/
  settings.json
```

`.contextkit/` is the technical manager binding. The other top-level folders are
visible because they are the agent project's body: its live context, supporting
materials, repeatable procedures, and capability envelopes.

The default binding is intentionally minimal:

```toml
version = 1
type = "agent-project"

[targets.codex]
output = ".codex/generated/context.md"

[targets.claude]
output = ".claude/rules/CONTEXT.md"
```

The standard source folders are `context/`, `assets/`, `routines/`, and
`capabilities/`. Add a `[sources]` table only when a project deliberately
overrides one of those paths.

`.gitignore` and `.env.local` are technical bootstrap files. `contextkit init`
creates the local env file as a non-secret template and makes sure git ignores
local env, generated runtime context, and capability state.

Context files are Markdown files with front matter:

```yaml
---
title: Human title
description: One-line routing description used by the model to decide when to load it.
load: inline|stub
order: 100
---
```

`inline` files are emitted fully into compiled context. `stub` files are emitted
as title, path, and description only. Files sort by numeric `order`, then path.

## v0 Scope

The current implementation covers the local, repo-backed agent body:

- project binding through `.contextkit/config.toml`;
- Codex and Claude context compilation;
- thin hook installation;
- native routine index inclusion from `routines/**/*.md` front matter;
- native capability index inclusion from `capabilities/settings.json`,
  installed capability snapshots, and visible project envelopes;
- advisory audit reports with `--write` persistence under `assets/audits/`.

Legacy dot-folder projects are migration inputs, not runtime defaults. Rename
`.context`, `.assets`, `.routines`, and `.capabilities` to their visible forms
before building with ContextKit.

Migration and groom apply modes are intentionally conservative in v0.
