# Destructive Operations Guide

Destructive operations erase, overwrite, or irreversibly mutate project data.
Database reset commands remain destructive inside wrappers such as Docker, SSH,
CI, Railway, or a remote shell.

## Exact Authorization Required

Do not run a destructive command unless the user has explicitly authorized that
exact command against that exact target.

Authorization must identify:

- command;
- environment or database;
- expected destructive effect;
- whether the data is disposable.

If the user authorizes one operation, that authorization does not carry to a
neighboring command or another environment.

## Database-Destructive Families

Treat these as destructive by default:

```text
php artisan migrate:fresh
php artisan migrate:refresh
php artisan migrate:reset
php artisan migrate:rollback
php artisan db:wipe
```

Also treat equivalent commands in other stacks as destructive: dropping schemas,
resetting migrations, truncating production-like data, deleting queues, clearing
object stores, or rewriting remote state.

The wrapper does not make the command safer:

```text
docker exec ...
ssh host -- ...
railway run ...
pnpm script-that-runs-reset
```

## Hypothesis Testing Is Not Authorization

"Let me reset it to see whether the failure is pre-existing" is not a valid
reason. Prefer non-destructive alternatives:

- read the migration and its tests;
- run against a disposable throwaway database;
- inspect `migrate:status` or equivalent;
- create a temporary container or isolated schema;
- compare code paths without deleting data.

## If Authorization Is Granted

Before running, restate:

1. the exact command;
2. the exact target;
3. the data that may be erased;
4. the confirmation you received.

Then run only that operation. If anything changes about the command or target,
stop and ask again.

## If A Guard Blocks The Command

Do not work around a harness, shell, CI, or policy block. Stop, explain the
blocked command and target, and ask the user how to proceed.
