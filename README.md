# ContextKit

ContextKit is a standalone manager for repo-backed agent project memory. It
standardizes how an agent project's durable context is structured, compiled into
Codex or Claude runtime context, audited, and migrated.

ContextKit is deliberately higher-rank than a normal capability. Capabilities
remain separate tools; ContextKit discovers and indexes them as one layer of an
agent project.

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
contextkit install-hooks --target codex --target claude
contextkit build --target all
contextkit doctor
contextkit audit
contextkit audit --write
contextkit guide authoring
```

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
visible because they are the agent project's body and memory, not hidden tool
internals.

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

The current implementation covers the local/repo-backed step:

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
