# Bootstrap Guide

Bootstrap establishes the ContextKit technical binding, visible project body,
host bindings, generated runtime context, and first validation pass.

## Main Command

Run from the project root:

```sh
contextkit bootstrap
```

Effects:

- initializes Git when `.git` is absent and the directory has no project files;
- creates a pre-bootstrap Git checkpoint before project file changes when
  `.git` is absent and the directory already contains files;
- creates missing `.contextkit/`, `.gitignore`, `.env.local`, `context/`,
  `assets/`, `routines/`, and `capabilities/` entries;
- leaves existing project body files in place;
- installs Codex and Claude bindings;
- builds generated runtime context;
- runs doctor;
- runs audit.

Safety contract:

- existing non-git project files get a checkpoint before ContextKit changes
  project files;
- `--yes` approves checkpoint creation and managed hook replacement;
- visible body files are created only when absent;
- ContextKit-managed generated files are rebuilt from source;
- existing non-ContextKit files in managed hook paths require confirmation
  before replacement;
- invalid host JSON blocks bootstrap until repaired;
- dot body folders block bootstrap until migration is planned.

## New Project

Start inside an empty directory:

```sh
contextkit bootstrap
```

Created body:

- `.contextkit/config.toml`;
- `.contextkit/README.md`;
- `.contextkit/audits/`;
- `.gitignore` guards;
- `.env.local` placeholder;
- `context/` skeleton files;
- `assets/sessions/`, `assets/plans/`, `assets/research/`;
- `routines/`;
- `capabilities/settings.json`.

Default config:

```toml
version = 1
type = "agent-project"

[targets.codex]
output = ".codex/generated/context.md"

[targets.claude]
output = ".claude/rules/CONTEXT.md"
```

Standard source folders are implicit: `context/`, `assets/`, `routines/`,
`capabilities/`. Add `[sources]` only for deliberate path overrides.

## Existing Project

Run from the repository root:

```sh
contextkit bootstrap
```

Existing visible body files remain in place. Missing binding files, guards,
host bindings, generated context, and skeleton files are added.

If `.git` is absent, bootstrap creates a checkpoint before ContextKit changes
project files:

```sh
git init
git add -A
git commit -m "ContextKit pre-bootstrap checkpoint"
```

The checkpoint respects existing `.gitignore` rules and ContextKit local secret
guards.

For dot body folders, inspect the migration plan:

```sh
contextkit migrate --plan
```

Rename dot body folders to visible body folders before bootstrap completes:

```sh
git mv .context context
git mv .assets assets
git mv .routines routines
git mv .capabilities capabilities
```

If `.assets/` and `assets/` both exist, merge manually. Preserve historical
material in `assets/`; promote only durable live facts into `context/`.

## Targeted Bootstrap

Bootstrap one host binding:

```sh
contextkit bootstrap --target codex
```

```sh
contextkit bootstrap --target claude
```

Bootstrap both host bindings explicitly:

```sh
contextkit bootstrap --target codex --target claude
```

## Component Commands

Create missing binding and body files:

```sh
contextkit init
```

Install host bindings:

```sh
contextkit install-hooks --target codex --target claude
```

Build generated runtime context:

```sh
contextkit build --target all
```

Check shape and bindings:

```sh
contextkit doctor
```

Run the advisory audit:

```sh
contextkit audit
```

## How The Agent Learns ContextKit

Agents learn ContextKit through generated runtime context, not through ambient
memory and not through copied doctrine files.

Codex reads `.codex/generated/context.md`. Claude reads
`.claude/rules/CONTEXT.md`. Those files contain:

- the manager header;
- rebuild and doctor commands;
- always-on ContextKit operating runtime;
- inline project context;
- metadata stubs for on-demand project context;
- routine index;
- capability index.

Generated files are build artifacts. Edit source files, then rebuild.

## Bootstrap Quality Bar

A project is bootstrapped when:

- `contextkit bootstrap` completes;
- `contextkit doctor` reports ok;
- `contextkit build --target all` writes configured targets;
- `contextkit audit` has no unreviewed findings;
- `.env.local` exists and is ignored;
- generated context files are ignored or intentionally tracked by project policy;
- visible body folders are present;
- dot body folders are absent.
