# Machine-Readable Context

Power: automation without guesswork.

Authoring surfaces that need routing, compilation, or validation expose
metadata in a predictable machine-readable form.

Decision Question: does this artifact need explicit metadata so tools can
route, compile, validate, or repair it without guessing?

## Law

The machine should not infer critical routing metadata from prose when the
author can declare it explicitly.

Metadata lives beside the artifact it describes. It is not a parallel doctrine
source; it is the structured handle that lets tools find and manage the owner.

## Failure Signs

- load behavior is hidden in prose;
- a compiler relies on filename folklore;
- a tool scrapes prose for rule source, status, or affected paths.
