# Hooks Guide

`contextkit install-hooks --target codex` writes a thin Codex adapter that calls
`contextkit build --target codex`. `--target claude` wires a Claude SessionStart
hook that builds `.claude/rules/CONTEXT.md`.
