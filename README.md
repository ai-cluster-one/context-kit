# ContextKit

ContextKit turns a Git repository into an agent-ready project.

It gives agents a stable project body: live context, supporting evidence,
repeatable routines, tool metadata when tools are enabled, and generated runtime
context for hosts such as Codex and Claude.

Use ContextKit when multiple agents, hosts, or sessions need the same source of
truth for how a project works and how agent context is delivered.

## What You Get

- a visible project structure for agent context;
- generated runtime context for Codex and Claude;
- always-on operating doctrine loaded from ContextKit;
- on-demand guides for authoring, validation, audits, routines, assets,
  migration, hooks, and destructive operations;
- advisory audits that point to the rule source for each finding;
- generated runtime context rebuilt from source, never edited by hand.

## Quick Start

Install:

```sh
curl -fsSL https://raw.githubusercontent.com/ai-cluster-one/context-kit/main/install.sh | sh
```

Bootstrap the current directory:

```sh
contextkit bootstrap
```

`bootstrap` creates missing ContextKit body files, installs Codex and Claude
bindings, builds generated context, then runs doctor and audit. Existing body
files stay in place. Existing non-ContextKit files in managed hook paths require
confirmation before replacement.

When `.git` is absent and the directory already contains files, bootstrap stops
before project files change and asks to create a pre-bootstrap Git checkpoint.
The checkpoint initializes Git, stages current files, and commits
`ContextKit pre-bootstrap checkpoint`.

For non-interactive bootstrap, `contextkit bootstrap --yes` approves checkpoint
creation and managed hook replacement.

Bootstrap a repository that already exists from its root:

```sh
contextkit bootstrap
```

If bootstrap reports dot body folders, inspect the migration plan:

```sh
contextkit migrate --plan
```

For local development, run the checked-out script directly:

```sh
./bin/contextkit help
```

## Project Body

```text
.contextkit/
  README.md
  config.toml
  audits/
.gitignore
.env.local
context/
  identity/
  guidelines/
  architecture/
assets/
  sessions/
  plans/
  research/
routines/
capabilities/
  settings.json
```

Layer roles:

- `.contextkit/` - technical binding, config, and ContextKit-native audit
  reports;
- `context/` - live project doctrine and routing surface;
- `assets/` - evidence, plans, research, and session history;
- `routines/` - repeatable procedures surfaced into runtime context;
- `capabilities/` - project envelopes for enabled tools;
- `.codex/` and `.claude/` - generated host runtime context and hooks.

## Runtime Context

ContextKit compiles source files into host-specific generated context:

- Codex: `.codex/generated/context.md`
- Claude: `.claude/rules/CONTEXT.md`

Generated files are build artifacts. Edit the source body, then rebuild:

```sh
contextkit build --target all
```

ContextKit's own operating doctrine and guides live in this repository under
`doctrine/`. They are not copied into initialized projects. The manager reads
them from the checkout, from the global install at `~/.contextkit/doctrine`, or
from `CONTEXTKIT_DOCTRINE_DIR`.

## Context Files

Context files are Markdown files with front matter:

```yaml
---
title: Human title
description: One-line routing description used by the model to decide when to load it.
load: inline|stub
order: 100
---
```

`inline` files are emitted fully into generated context. `stub` files are emitted
as title, path, and description only. Files sort by numeric `order`, then path.

Use `contextkit guide authoring` for placement, naming, load modes, and quality
rules.

## Core Commands

Bootstrap a project end to end:

```sh
contextkit bootstrap
```

Initialize missing binding and body files:

```sh
contextkit init
```

Adopt only the ContextKit binding in an existing project body:

```sh
contextkit adopt
```

Inspect a dot-folder or mixed-layout migration:

```sh
contextkit migrate --plan
```

Install Codex and Claude host bindings:

```sh
contextkit install-hooks --target codex --target claude
```

Build all generated runtime contexts:

```sh
contextkit build --target all
```

Check project shape and bindings:

```sh
contextkit doctor
```

Run the advisory audit:

```sh
contextkit audit
```

Write an audit report under `.contextkit/audits/`:

```sh
contextkit audit --write
```

Read the bootstrap guide:

```sh
contextkit guide bootstrap
```

Read the authoring guide:

```sh
contextkit guide authoring
```

Read the validation guide:

```sh
contextkit guide validation
```

Read the destructive-operations guide:

```sh
contextkit guide destructive
```

Command outputs point to rule-source guides. Load the named guide, edit source
files, then rerun the command.

## Default Config

The default binding is intentionally minimal:

```toml
version = 1
type = "agent-project"

[targets.codex]
output = ".codex/generated/context.md"

[targets.claude]
output = ".claude/rules/CONTEXT.md"
```

Standard source folders are `context/`, `assets/`, `routines/`, and
`capabilities/`. Add a `[sources]` table only when a project deliberately
overrides one of those paths.

`.gitignore` and `.env.local` are technical bootstrap files. `contextkit init`
creates a non-secret `.env.local` template and gitignore guards for local env,
generated runtime context, and capability state.

## Capabilities

Capabilities are separate tool packages managed by the
[capabilities project](https://github.com/ai-cluster-one/capabilities).

When a repository has a `capabilities/` project envelope, ContextKit reads the
enabled tool set and includes tool awareness in generated runtime context.
Capability implementation, release, credentials, connections, and capability
audit live in the capabilities project and in capability-owned guides.

## v0 Scope

The current implementation covers the local, repo-backed agent body:

- project binding through `.contextkit/config.toml`;
- idempotent bootstrap for git init, missing body creation, hook install,
  build, doctor, and audit;
- Codex and Claude context compilation;
- thin hook installation;
- routine index inclusion from `routines/**/*.md` front matter;
- capability index inclusion from `capabilities/settings.json`, installed
  capability snapshots, and visible project envelopes;
- advisory audit reports with `--write` persistence under `.contextkit/audits/`;
- on-demand doctrine guides loaded from the ContextKit source/install, not copied
  into each project.

Legacy dot-folder projects are migration inputs, not runtime defaults. Rename
`.context`, `.assets`, `.routines`, and `.capabilities` to their visible forms
before building with ContextKit.

Migration and groom apply modes are intentionally conservative in v0.
