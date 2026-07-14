# Bootstrap Guide

Use this guide when initializing or adopting a ContextKit project body.

This guide is the operational rule source for bootstrap and adoption. It applies Visible Body, Project Stewardship, Bounded Compatibility, Convergent Operations, Generated Output, and Human Gates.

Use `contextkit help` for exact command syntax.

## Goal

Bootstrap establishes:

- ContextKit binding under `.contextkit/`;
- ignored local env and generated-state guards;
- visible body layers: `context/`, `assets/`, `routines/`, `capabilities/`;
- configured host bindings;
- generated runtime context;
- first doctor/build/audit pass.

Existing project material has standing. Inspect before changing it. Visible body files are created only when absent. Existing body files remain in place.

## Main Flow

From the project root:

```sh
contextkit bootstrap
```

Bootstrap creates missing binding and empty body layers, installs configured host bindings, builds generated context, runs doctor, and runs audit.

An absent `memory/` directory is healthy. Bootstrap, initialization, and templates do not create it; the first memory capture or import creates it when needed.

If a directory has files but no Git repository, bootstrap asks for a pre-bootstrap Git safeguard before ContextKit changes project files. `--yes` approves that safeguard and managed hook replacement.

Starter context templates are opt-in:

```sh
contextkit bootstrap --with-template
```

## Component Flows

Use component commands when you need a smaller change:

```sh
contextkit init
contextkit init --with-layers
contextkit init --with-template
contextkit adopt
contextkit adopt --with-layers
contextkit adopt --with-template
contextkit install-hooks --target codex --target claude
contextkit build --target all
contextkit doctor
contextkit audit
```

The CLI owns exact option behavior. This guide owns when and why to use the flows.

## Existing Projects

Existing visible body files remain in place. Missing binding files, guards, host bindings, generated context, and empty layers may be added.

Legacy dot folders are migration inputs:

```text
.context/       -> context/
.assets/        -> assets/
.routines/      -> routines/
.capabilities/  -> capabilities/
```

Inspect migration before moving files:

```sh
contextkit migrate --plan
```

Merge collisions manually. Preserve historical material in `assets/`; promote only durable live facts into `context/`.

## Host Delivery

Agents learn project context through generated runtime context. Codex and Claude read generated targets from host bindings. Generated files are build artifacts: edit source files, then rebuild.

## Quality Bar

A project is bootstrapped when doctor is ok, generated context builds, audit has no unreviewed findings, local env and generated files are ignored or intentionally tracked, visible body folders are present, and legacy dot body folders are not canonical.
