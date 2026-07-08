# Hooks Guide

Use this guide when installing, reviewing, or repairing host bindings.

Rule owners: Host-Neutral Core, Generated Output, Hooks Standard, and
Operational Provenance.

## Role

Host bindings deliver generated ContextKit output to agent runtimes.

Hooks are thin adapters. They call `contextkit build` and write configured
generated targets. Project doctrine lives in source files.

## Codex

```sh
contextkit install-hooks --target codex
```

The Codex adapter rebuilds generated context from the project body. Codex
wiring belongs under `.codex/`; source doctrine belongs in the visible body.

## Claude

```sh
contextkit install-hooks --target claude
```

The Claude hook rebuilds its configured generated target. The generated file is
delivery output, not source truth.

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
