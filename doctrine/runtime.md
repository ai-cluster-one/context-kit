# ContextKit Operating Doctrine

## Bootstrap and validation

- New project sequence: `git init`, `contextkit init`, `contextkit install-hooks --target codex --target claude`, `contextkit doctor`, `contextkit build --target all`, `contextkit audit`.
- Existing project sequence: `contextkit migrate --plan`, `contextkit adopt`, move legacy dot body folders to visible folders, install hooks, then run doctor/build/audit.
- After changing the agent body, run `contextkit doctor`, `contextkit build --target all`, and `contextkit audit` before committing.
- Generated context files are build artifacts. Do not edit `.codex/generated/context.md` or `.claude/rules/CONTEXT.md` by hand.

## Authoring rules

- One durable fact has one live home. When facts conflict, update the owning file instead of duplicating a second truth.
- Live source of truth beats documentation when they disagree.
- `context/` is current doctrine. Every context Markdown file needs front matter: `title`, specific one-line `description`, `load: inline|stub`, and numeric `order`.
- Use `load: inline` only for always-needed constraints. Use `load: stub` for discoverable context that should be loaded on demand.
- Do not use Markdown links between context files as routing. Routing belongs in descriptions, generated indexes, and explicit loading.
- `assets/` is historical evidence and supporting material, not live doctrine. Promote durable facts into the live owning layer; do not rewrite old assets just to make them current.
- `routines/` holds repeatable procedures. A routine describes ordered work and when to run it; it should not duplicate tool contracts, identifiers, or durable source-system doctrine.
- `capabilities/` is an external tool layer that ContextKit indexes when present. Capability creation, validation, audit, and internal doctrine belong to the capabilities manager/repo, not to ContextKit.
- Do not store loose work in progress in the repo. Durable work belongs in the project's chosen work system or in a deliberate asset/audit artifact.

## Audit and repair

- Use `contextkit audit` for the whole live context and `contextkit audit-file <path>` for one file.
- Fix missing metadata, weak descriptions, duplicate durable facts, internal context links, inline bloat, and content that lives at the wrong layer.
- Persist formal reports with `contextkit audit --write` under `assets/audits/`.
- After remediation, rebuild and audit again until the project body is coherent.
