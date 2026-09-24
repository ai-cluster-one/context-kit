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

The Codex adapter rebuilds generated context from the project body and prints the generated target to standard output. Codex adds synchronous `SessionStart` output to the session as developer context, and the managed hook sets `additionalContextLimit` to `0`, so the target is delivered whole and only the model context window bounds it. When the build or the read fails, the adapter emits nothing and exits non-zero, so a session never proceeds as though context had loaded.

Installing the hook keeps exactly one managed `SessionStart` hook: an existing hook that calls the adapter is adopted, and a duplicate invocation of the adapter is removed so the context is delivered once. The managed hook runs through a login shell so the installed manager resolves by name, and the manager then selects a supported Python itself. The adapter and the manager ship together, so install the current ContextKit before installing the hook. Codex records trust for a hook command, so approve the managed hook once in Codex after it changes; an unapproved hook does not run and the session starts without generated context.

ContextKit owns no Codex project-document settings. Installing the hook removes a `project_doc_fallback_filenames` entry that names the generated target, because Codex rejects a fallback filename that carries a path. When that entry is the last one, the whole assignment goes and Codex keeps its own project-document defaults; a comment on that line stays. Every other Codex setting stays with its owner, and an assignment ContextKit cannot locate safely is preserved and reported instead of rewritten.

Codex wiring belongs under `.codex/`; source doctrine belongs in the visible body.

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

`contextkit doctor` reports an installed Codex binding that cannot deliver generated context. Repair it by installing the hook again, then start a new host session so the repaired hook runs.

After hook changes:

```sh
contextkit doctor
contextkit build --target all
```
