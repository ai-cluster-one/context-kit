# Hooks Guide

Host bindings deliver generated ContextKit output to agent runtimes.

Hooks are delivery mechanisms. A hook is a thin adapter that calls
`contextkit build`. Project doctrine lives in source files.

## Codex

```sh
contextkit install-hooks --target codex
```

This writes the Codex adapter that rebuilds `.codex/generated/context.md` from
the project body. Codex-specific wiring belongs under `.codex/`; source doctrine
belongs under `context/`.

## Claude

```sh
contextkit install-hooks --target claude
```

This wires a Claude SessionStart hook that rebuilds
`.claude/rules/CONTEXT.md`. The generated file is the Claude delivery target, not
the source of truth.

## Hook Rules

- One generated file has one writer: ContextKit.
- Do not hand-edit generated context to fix a source problem.
- Do not copy ContextKit doctrine into the project to make a hook work.
- Keep host-specific paths in target config and adapters.
- Keep host-neutral doctrine in `context/` or the ContextKit `bundle/`.

After hook changes:

```sh
contextkit doctor
contextkit build --target all
```
