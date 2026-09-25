# Hooks Guide

Use this guide when installing, reviewing, or repairing host bindings.

This guide is the operational rule source for host bindings. It applies Host-Neutral Core, Generated Output, and Operational Provenance.

## Role

Host bindings connect agent runtimes to generated ContextKit output.

When ContextKit creates a new Claude settings file, it disables Claude automatic memory so project continuity routes through ContextKit memory. When Claude settings already exist, preserve their memory policy and merge only the managed hook. Do not change Codex memory settings.

When project memory uses `CONTEXTKIT_MEMORY_DIR`, ensure the host session and build hook receive the same environment anchor. Verify it from that environment with `contextkit memory status`.

ContextKit writes one generated context file, `.contextkit/generated/context.md` unless `[output] context` in `.contextkit/config.toml` names another project path. Every host reads that same file through its own native instruction discovery, reached by a symlink ContextKit owns. No hook delivers the context: each host loads it itself, keeps one copy per session, and carries a changed file into a resumed session on its own.

Hooks are thin adapters. They run `contextkit session-start --host <host>`, which rebuilds the generated file and prints a short session notice only when the session needs one. A host reads its instructions before its session hook runs, so a rebuild that changes the file reaches the next new or resumed session; the notice tells the current session its copy is stale. Project doctrine lives in source files.

Installing a binding also builds the generated file and its host link, so the first session after installation loads it. Git ignores both, so in a fresh clone the first session hook creates them and its notice asks for a new session. ContextKit replaces only a missing path, a dangling link, its own link, or generated context from an earlier release; any other file at a link path stays with its owner and is reported. The generated file itself never overwrites a file ContextKit did not generate, and it cannot live inside the source body.

## Codex

```sh
contextkit install-hooks --target codex
```

Codex loads project docs only by filename from the project root, so ContextKit links `.contextkit.md` at the root to the generated file and lists that name in `project_doc_fallback_filenames` in `.codex/config.toml`. It also raises `project_doc_max_bytes` to a budget that holds the generated file whole; Codex truncates project docs beyond that budget. Every other Codex setting stays with its owner, and an assignment ContextKit cannot locate safely is preserved and reported instead of rewritten.

Codex reads a project's `.codex/` layer only in a folder it trusts, and runs a project hook only when its trust record matches the hook's current definition. A headless session has nobody to approve either, so installing the binding records both in the Codex user config (`$CODEX_HOME/config.toml`, default `~/.codex/config.toml`): the folder's `trust_level` and the managed hook's `trusted_hash`, computed exactly as Codex computes it. A folder the user marked untrusted stays untrusted. Pass `--no-trust` to leave the Codex user config alone and approve both in Codex instead.

A root `AGENTS.md` or `AGENTS.override.md` takes precedence over `.contextkit.md`, and Codex then loads no generated context. The session notice and `contextkit doctor` both say so; moving that file's durable content into the body is the user's decision.

Codex wiring belongs under `.codex/`; source doctrine belongs in the visible body.

## Claude

```sh
contextkit install-hooks --target claude
```

ContextKit links `.claude/rules/CONTEXT.md` to the generated file, and Claude loads it as a project rule. The Claude hook runs the same session refresh.

## Foreign Instruction Files

Hosts also load instruction files ContextKit does not generate: `AGENTS.md`, `AGENTS.override.md`, `CLAUDE.md`, and `CLAUDE.local.md` at the project root or in any subfolder Git sees, `.claude/CLAUDE.md`, and other files under `.claude/rules/`. They can repeat, contradict, or override the generated context. The generated context names every one it finds and tells the agent to raise them with the user at the start of the session; `contextkit doctor` and `contextkit migrate --plan` list them too. Keeping, migrating, or removing them is the user's decision.

## Hook Rules

- One generated file has one writer: ContextKit.
- Do not hand-edit generated context.
- Do not copy ContextKit doctrine into a project to make a hook work.
- Keep host-specific paths in host links and adapters.
- Keep host-neutral doctrine in source.

`contextkit doctor` reports an installed binding whose host cannot load the generated context: a missing or foreign link, missing Codex project-doc settings or trust, a budget smaller than the file, or a shadowing root instruction file. Repair it by installing the binding again, then start a new host session.

After hook changes:

```sh
contextkit doctor
contextkit build
```
