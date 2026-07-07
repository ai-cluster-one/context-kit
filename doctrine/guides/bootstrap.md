# Bootstrap Guide

## New project

Start from the repository root:

```sh
git init
contextkit init
contextkit install-hooks --target codex --target claude
contextkit doctor
contextkit build --target all
contextkit audit
```

`contextkit init` creates the technical binding (`.contextkit/`), local bootstrap
guards (`.gitignore`, `.env.local`), and the visible agent body folders:
`context/`, `assets/`, `routines/`, and `capabilities/`.

## Existing project

Start with a plan, then move deliberately:

```sh
contextkit migrate --plan
contextkit adopt
```

Rename legacy dot body folders to their visible forms:

```sh
git mv .context context
git mv .routines routines
git mv .capabilities capabilities
```

If `.assets/` and `assets/` both exist, merge them manually so historical
material is preserved, then remove `.assets/`. After the body is visible:

```sh
contextkit install-hooks --target codex --target claude
contextkit doctor
contextkit build --target all
contextkit audit
```

## How the agent learns ContextKit

ContextKit is passed to agents through host bindings and generated context, not
through ambient memory. Codex reads `.codex/generated/context.md`; Claude reads
`.claude/rules/CONTEXT.md`. Those files contain the manager header, rebuild
command, doctor command, help command, and indexes for context, routines, and
capabilities. Do not edit generated files by hand.
