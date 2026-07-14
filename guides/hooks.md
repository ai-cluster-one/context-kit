# Hooks Guide

Use this guide when installing, reviewing, or repairing host bindings.

This guide is the operational rule source for host bindings. It applies Host-Neutral Core, Generated Output, and Operational Provenance.

## Role

Host bindings deliver generated ContextKit output to agent runtimes.

When ContextKit creates a new Claude settings file, it disables Claude automatic memory so project continuity routes through ContextKit memory. When Claude settings already exist, preserve their memory policy and merge only the managed hook. Do not change Codex memory settings.

When project memory uses `CONTEXTKIT_MEMORY_DIR`, ensure the host session and build hook receive the same environment anchor. Verify it from that environment with `contextkit memory status`.

Hooks are thin adapters. They call `contextkit build` and write configured generated targets. Project doctrine lives in source files.

## Codex

```sh
contextkit install-hooks --target codex
```

The Codex adapter rebuilds generated context from the project body. Codex wiring belongs under `.codex/`; source doctrine belongs in the visible body.

## Claude

```sh
contextkit install-hooks --target claude
```

The Claude hook rebuilds its configured generated target. The generated file is delivery output, not source truth.

## Hook Rules

- One generated file has one writer: ContextKit.
- Do not hand-edit generated context.
- Do not copy ContextKit doctrine into a project to make a hook work.
- Keep host-specific paths in target config and adapters.
- Keep host-neutral doctrine in source.

After hook changes:

```sh
contextkit doctor
contextkit build --target all
```
