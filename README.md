# ContextKit

ContextKit turns a Git repository into an agent-ready project.

It gives agents a stable project body: live context, supporting evidence, repeatable routines, tool metadata when tools are enabled, and generated runtime context for hosts such as Codex and Claude.

Use ContextKit when multiple agents, hosts, or sessions need the same source of truth for how a project works and how agent context is delivered.

## What You Get

- a visible project structure for agent context;
- generated runtime context for Codex and Claude;
- optional global context shared by multiple projects;
- always-on operating runtime loaded from the ContextKit bundle;
- generated guide menu in runtime context;
- on-demand guides for authoring, global context, validation, audits, routines, assets, migration, hooks, and destructive operations;
- starter context templates for project onboarding;
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

`bootstrap` creates missing ContextKit binding and empty body layers, installs Codex and Claude bindings, builds generated context, then runs doctor and audit. Existing body files stay in place. Existing non-ContextKit files in managed hook paths require confirmation before replacement.

Bootstrap does not create placeholder context files unless requested:

```sh
contextkit bootstrap --with-template
```

When `.git` is absent and the directory already contains files, bootstrap stops before project files change and asks to create a pre-bootstrap Git checkpoint. The checkpoint initializes Git, stages current files, and commits `ContextKit pre-bootstrap checkpoint`.

For non-interactive bootstrap, `contextkit bootstrap --yes` approves checkpoint creation and managed hook replacement.

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

# Optional external source configured per project:
~/contextkit-global/
```

Layer roles:

- `.contextkit/` - technical binding, config, and ContextKit-native audit reports;
- `context/` - live project doctrine and routing surface;
- configured global context - live doctrine inherited by every project that opts into the external source;
- `assets/` - evidence, plans, research, and session history;
- `routines/` - repeatable procedures surfaced into runtime context;
- `capabilities/` - project envelopes for enabled tools;
- `.codex/` and `.claude/` - generated host runtime context and hooks.

## Product Source Layout

ContextKit separates the sources it ships:

- `THESIS.md` - the worldview of ContextKit.
- `bundle/` - shipped always-on runtime block.
- `guides/` - shipped on-demand operating and authoring guides.
- `templates/` - starter project-body files for onboarding and initialization.
- `bin/` - the executable manager and command contracts.
- `install.sh` - the installer for the manager, runtime, guides, and templates.

## Runtime Context

ContextKit compiles project context and an optional configured global context source into host-specific generated context:

- Codex: `.codex/generated/context.md`
- Claude: `.claude/rules/CONTEXT.md`

Generated files are build artifacts. Edit the source body, then rebuild:

```sh
contextkit build --target all
```

ContextKit's shipped runtime block lives under `bundle/`. Guides live under `guides/`. The manager reads them from the checkout, from the global install under `~/.contextkit/`, or from `CONTEXTKIT_BUNDLE_DIR` and `CONTEXTKIT_GUIDES_DIR`.

Generated runtime context includes the full runtime block and a generated Guide Menu. Guide bodies are loaded on demand with `contextkit guide <topic>`.

Global context is enabled per project with `sources.global_context` in `.contextkit/config.toml`. ContextKit recursively reads its Markdown files through the same front-matter, load-mode, and order contract as project `context/`. Use `contextkit guide global-context` for ownership, path, ordering, and validation rules.

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

`inline` files are emitted fully into generated context. `stub` files are emitted as title, path, and description only. Files sort by numeric `order`, then path.

Use `contextkit guide authoring` for placement, naming, load modes, and quality rules.

Use `contextkit guide global-context` before placing doctrine that should be inherited unchanged by multiple projects.

## Core Commands

Bootstrap a project end to end:

```sh
contextkit bootstrap
```

Initialize only the ContextKit binding:

```sh
contextkit init
```

Create empty project layers as well:

```sh
contextkit init --with-layers
```

Create empty layers plus starter context templates:

```sh
contextkit init --with-template
```

Adopt only the ContextKit binding in an existing project body:

```sh
contextkit adopt
```

Adopt binding and create empty layers in an existing project body:

```sh
contextkit adopt --with-layers
```

Adopt binding and create starter context templates too:

```sh
contextkit adopt --with-template
```

Initialization modes are explicit:

| Command                                | Creates                                                                               |
| -------------------------------------- | ------------------------------------------------------------------------------------- |
| `contextkit init` / `contextkit adopt` | `.contextkit/config.toml`, `.contextkit/README.md`, `.gitignore` guards, `.env.local` |
| `--with-layers`                        | binding plus empty `context/`, `assets/`, `routines/`, and `capabilities/` layers     |
| `--with-template`                      | binding, empty layers, and starter context files                                      |

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

Read the global-context guide:

```sh
contextkit guide global-context
```

Read the validation guide:

```sh
contextkit guide validation
```

Read the destructive-operations guide:

```sh
contextkit guide destructive
```

List starter templates:

```sh
contextkit templates
```

Command outputs point to rule-source guides. Load the named guide, edit source files, then rerun the command.

## Default Config

The default binding is intentionally minimal:

```toml
version = 1
type = "agent-project"

[sources]
# Optional shared doctrine outside this project:
# global_context = "~/contextkit-global"

[targets.codex]
output = ".codex/generated/context.md"

[targets.claude]
output = ".claude/rules/CONTEXT.md"
```

Default project source folders are `context/`, `assets/`, `routines/`, and `capabilities/`. `sources.global_context` is an explicit opt-in to one external shared-doctrine directory; omit it when the project has no global source.

`.gitignore` and `.env.local` are technical bootstrap files. Plain `contextkit init` creates only the binding files, a non-secret `.env.local` template, and gitignore guards for local env, generated runtime context, and capability state. Empty source layers require `contextkit init --with-layers`. Starter context templates require `contextkit init --with-template`.

## Capabilities

Capabilities are separate tool packages managed by the [capabilities project](https://github.com/ai-cluster-one/capabilities).

When a repository has a `capabilities/` project envelope, ContextKit reads the enabled tool set and includes tool awareness in generated runtime context. Capability implementation, release, credentials, connections, and capability audit live in the capabilities project and in capability-owned guides.

## v0 Scope

The current implementation covers the local, repo-backed agent body:

- project binding through `.contextkit/config.toml`;
- idempotent bootstrap for git init, binding and empty layer creation, hook install, build, doctor, and audit;
- Codex and Claude context compilation;
- optional recursive global-context compilation from `sources.global_context`;
- thin hook installation;
- routine index inclusion from `routines/**/*.md` front matter;
- capability index inclusion from `capabilities/settings.json`, installed capability snapshots, and visible project envelopes;
- advisory audit reports with `--write` persistence under `.contextkit/audits/`;
- generated guide menu and on-demand guides loaded from ContextKit source/install;
- starter template gallery for project onboarding.

Legacy dot-folder projects are migration inputs, not runtime defaults. Rename `.context`, `.assets`, `.routines`, and `.capabilities` to their visible forms before building with ContextKit.

Migration and groom apply modes are intentionally conservative in v0.
