# Bootstrap Guide

Use this guide when creating a new ContextKit project body or adopting an
existing repository.

Bootstrap has two jobs:

1. create the visible project body (`context/`, `assets/`, `routines/`,
   `capabilities/`);
2. install host bindings so the body is compiled into the agent's runtime
   context.

ContextKit doctrine itself is not copied into the project. The manager reads it
from the ContextKit checkout, global install, or `CONTEXTKIT_DOCTRINE_DIR`, then
injects the current version at build time.

## New Project

Start from the repository root:

```sh
git init
contextkit init
contextkit install-hooks --target codex --target claude
contextkit doctor
contextkit build --target all
contextkit audit
```

`contextkit init` creates:

- `.contextkit/config.toml`;
- `.contextkit/README.md`;
- `.contextkit/audits/`;
- `.gitignore` guards;
- `.env.local` placeholder;
- `context/` skeleton files;
- `assets/sessions/`, `assets/plans/`, `assets/research/`;
- `routines/`;
- `capabilities/settings.json`.

The default binding is minimal. Standard source folders are assumed; add
`[sources]` only when the project deliberately overrides a default path.

## Existing Project

Start with a plan:

```sh
contextkit migrate --plan
```

Then adopt only the technical binding:

```sh
contextkit adopt
```

Rename legacy dot body folders to visible body folders:

```sh
git mv .context context
git mv .routines routines
git mv .capabilities capabilities
```

If `.assets/` and `assets/` both exist, merge manually. Preserve historical
material; do not flatten it into live context just to make the migration quiet.

After the visible body exists:

```sh
contextkit install-hooks --target codex --target claude
contextkit doctor
contextkit build --target all
contextkit audit
```

## How The Agent Learns ContextKit

Agents learn ContextKit through generated runtime context, not through ambient
memory and not through copied doctrine files.

Codex reads `.codex/generated/context.md`. Claude reads
`.claude/rules/CONTEXT.md`. Those files contain:

- the manager header;
- rebuild and doctor commands;
- always-on ContextKit operating doctrine;
- inline project context;
- metadata stubs for on-demand project context;
- routine index;
- capability index.

Do not edit generated files by hand. Change the source body, then rebuild.

## Bootstrap Quality Bar

A project is bootstrapped when:

- `contextkit doctor` reports ok;
- `contextkit build --target all` writes all configured targets;
- `contextkit audit` has no unreviewed findings;
- `.env.local` exists and is ignored;
- generated context files are ignored or intentionally tracked by project policy;
- the visible body folders are present and legacy dot body folders are gone.
