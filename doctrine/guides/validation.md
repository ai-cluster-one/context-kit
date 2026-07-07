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

`audit` runs the machine pass over the project body. Use
`contextkit guide audit` for the audit procedure, then load the owning guide for
the layer being judged. Validation owns the sequence; the audit guide owns the
audit walk; the authoring guides own the layer rules.

Use `contextkit audit-file <path>` for a focused machine pass while editing, then
apply the guide named by `contextkit guide audit` for that path.

## Human Review Checklist

The machine checks are the floor. A human or agent review should also ask:

- Which guide owns the layer being reviewed?
- Did the reviewer load that guide before judging the file?
- Is every finding tied to the rule source that owns it?
- Did any issue cross layers and therefore require two rule sources?
- Did the repair change the owning source instead of generated output?
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
