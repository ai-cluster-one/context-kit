# Global Context Guide

Use this guide when configuring, authoring, validating, or repairing live doctrine shared by multiple ContextKit projects.

This guide is the operational rule source for the external global-context source. It applies One Fact One Home, Altitude, Semantic Anchors, Project Stewardship, and the context-file contract from `contextkit guide authoring`.

## Ownership

Put a durable fact in global context only when the same fact should govern every project that opts into the source. Keep project identity, architecture, constraints, and domain decisions in the owning project's `context/` tree.

Global context is another live doctrine source, not a fallback, copy, or override layer. Do not repeat a global fact locally to strengthen it. If global and project doctrine conflict, repair the owning source instead of relying on load order.

## Initialize A Source

Use `contextkit help` to discover the global-context initialization route and its live command behavior.

## Enable The Source

Add one optional entry to the project's `.contextkit/config.toml`:

```toml
[sources]
global_context = "~/contextkit-global"
```

The value may be an absolute path, a `~`-relative path, an exported environment-variable reference such as `${CONTEXTKIT_GLOBAL_CONTEXT_DIR}`, or a path relative to the project root. The resolved global directory and project must be separate, non-overlapping trees so recursive loading cannot absorb the project or neighboring repositories. Each project opts in explicitly; ContextKit does not discover a global source automatically.

Remove `sources.global_context` to disable the source for that project.

## File Contract

ContextKit recursively reads every `*.md` file under the configured directory. Global files use the same context-file contract as project context; use `contextkit guide authoring` for the schema, descriptions, body voice, semantic line breaks, load-mode judgment, and context quality.

Use `load: inline` only for compact doctrine needed in nearly every session across every participating project. Use `load: stub` for shared doctrine that should be discoverable and loaded only for relevant work.

Global and project files form one ordered stream. Files sort by numeric `order`; global files precede project files when `order` is equal; paths break remaining ties. This ordering provides a deterministic reading sequence, not override semantics.

## Build And Provenance

`contextkit build` reads the global directory at build time and compiles it into every requested host target. Generated context identifies each global inline source and exposes a loadable absolute path for each global stub.

ContextKit does not copy the global source into the project. Edit the owning global file and rebuild each participating project that should receive the change.

## Validation

Use `contextkit guide validation` and follow its live sequence from every configured project. Semantic ownership across global and project doctrine still requires human or agent review.

## Safety And Portability

Keep secrets, credentials, machine state, task queues, and personal scratch memory out of global context. Inline bodies are copied into generated host context, and stub paths are visible there.

Keep shared doctrine in a visible dedicated directory or repository, not inside ContextKit's hidden manager state. Prefer `~`, a stable relative anchor, or an exported environment variable over a hard-coded user-specific absolute path in shared configuration. The configuration owns the concrete location; authored doctrine owns only the durable meaning.

## Quality Bar

A global source is healthy when every included project should inherit its facts, each fact has one live owner, inline cost is justified across projects, stubs are loadable from generated paths, and every participating project passes the current validation guide.
