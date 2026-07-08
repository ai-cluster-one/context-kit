# Destructive Operations Guide

Use this guide before running commands that erase, overwrite, or irreversibly
mutate project data.

Rule owners: Human Gates, Project Stewardship, and the Destructive Operations
surface of the relevant project or tool.

## Authorization

Do not run a destructive command unless the user has explicitly authorized that
exact command against that exact target.

Authorization identifies:

- command;
- environment or database;
- expected destructive effect;
- whether the data is disposable.

Approval for one operation does not carry to a neighboring command, target, or
environment.

## Destructive Families

Treat database resets, schema drops, migration resets, truncation, queue
deletion, object-store deletion, and remote state rewrites as destructive.

Wrappers do not reduce the consequence. Docker, SSH, CI, Railway, pnpm scripts,
or remote shells can still run destructive operations.

## Safer Alternatives

Hypothesis testing is not authorization. Prefer reading the code, checking
status, using disposable throwaway data, creating isolated schemas, or comparing
code paths without deleting state.

## If Authorization Is Granted

Before running, restate the exact command, exact target, data that may be
erased, and confirmation received. Run only that operation. If the command or
target changes, stop and ask again.

## If A Guard Blocks The Command

Do not work around a harness, shell, CI, or policy block. Stop, explain the
blocked command and target, and ask how to proceed.
