# Hooks Standard

Rule source for host bindings and generated context delivery.

## Contract

Hooks are host-specific delivery adapters. They call ContextKit build commands
and write configured generated targets. They do not carry durable doctrine.

Host-specific wiring belongs under the host binding layer. Host-neutral doctrine
belongs in ContextKit source or the visible project body.

## Quality Bar

A hook is good when it is thin, rebuilds from source, identifies the generated
target, preserves host-specific configuration boundaries, and can be repaired by
editing the binding or source rather than generated output.
