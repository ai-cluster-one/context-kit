# Audit Guide

Use audits to bring the project body back into shape.

Commands:

```sh
contextkit audit
contextkit audit-file context/path/to/file.md
contextkit audit --write
```

`contextkit audit` is advisory by default. `contextkit audit --write` persists a
report under `.contextkit/audits/`.

Fix these classes first:

- missing or invalid front matter;
- weak routing descriptions;
- duplicate durable facts;
- internal context links used as routing;
- inline files that should be stubs;
- material living in the wrong layer;
- historical assets treated as live doctrine.

After remediation, run `contextkit build --target all` and `contextkit audit`
again. The goal is a coherent body, not a quiet report at any cost.
