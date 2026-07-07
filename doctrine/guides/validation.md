# Validation Guide

Use validation after initialization, migration, hook changes, or any meaningful
edit to `context/`, `assets/`, `routines/`, or `capabilities/`.

Validation has three layers:

```sh
contextkit doctor
contextkit build --target all
contextkit audit
```

## `doctor`: Shape And Binding

`doctor` checks whether the repository can be treated as a ContextKit agent
body. It validates:

- `.contextkit/config.toml`;
- `.contextkit/README.md`;
- `.gitignore` guards for env, generated context, Python cache, and capability
  state;
- `.env.local` presence;
- visible body layers: `context/`, `assets/`, `routines/`, `capabilities/`;
- `capabilities/settings.json`;
- legacy dot body folders that should be renamed;
- target output paths for Codex and Claude.

`doctor` does not validate the internals of a capability. It only confirms that
the project exposes a capability envelope layer. Capability implementation,
creation, release, credentials, connections, and capability audit live in the
capabilities manager/repo.

## `build`: Delivery To Hosts

`build --target all` proves the source body can compile into host runtime
context.

The compiler:

- reads ContextKit's always-on operating doctrine from the manager install or
  checkout;
- reads project `context/` files;
- inlines `load: inline` files;
- emits metadata stubs for `load: stub` files;
- generates routine and capability indexes;
- writes host-specific generated files.

Generated files are build artifacts. Edit source files, then rebuild. Do not fix
generated output by hand.

## `audit`: Coherence And Quality

`audit` judges the live context layer. It catches or hints at:

- missing or invalid front matter;
- weak routing descriptions;
- oversized inline files;
- duplicate durable facts;
- internal context links used as routing;
- assets treated as live doctrine;
- files that appear to live at the wrong context altitude;
- historical or comparative framing that should be rewritten as present doctrine;
- running task state inside live context.

Use `contextkit audit-file <path>` for a focused pass while editing.

## Human Review Checklist

The machine checks are the floor. A human or agent review should also ask:

- Does each file own exactly one domain?
- Would a future agent know when to load each stub?
- Is every always-on paragraph worth paying for in every session?
- Did any asset conclusion need promotion into `context/`?
- Did any routine copy a model that belongs in context?
- Did any context file copy a command contract that belongs to a tool?
- Did the change introduce host-specific assumptions that belong in hooks or
  targets instead?
- Did the change leave generated files unstaged?

## Validation Before Commit

Before committing:

```sh
contextkit doctor
contextkit build --target all
contextkit audit
git status --short
```

If validation fails, fix the source layer that owns the problem. Do not silence
the report by moving material to a less visible place.
