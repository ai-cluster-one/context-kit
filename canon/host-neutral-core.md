# Host-Neutral Core

Power: portability.

ContextKit doctrine is host-neutral. Host bindings are thin delivery adapters.

Decision Question: is this host-specific wiring, or host-neutral doctrine?

## Law

Keep host-specific paths, hooks, adapters, and generated targets in the binding
layer. Keep durable doctrine in ContextKit source or the visible project body.

Adding a host adds a delivery adapter, not a parallel doctrine system.

## Failure Signs

- a host hook contains durable doctrine;
- one host receives unique project law;
- adding a runtime requires rewriting canon.
