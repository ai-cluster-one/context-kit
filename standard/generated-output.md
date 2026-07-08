# Generated Output Standard

Rule source for host runtime files, generated indexes, and build artifacts.

## Contract

Generated output has one writer. It identifies its generator, source or config
owner, and rebuild or verification route when the artifact may be encountered
before the source.

Generated output is replaced deterministically, not patched in place. If output
is wrong, repair the source or generator and rebuild.

Tracked generated output is a deliberate project policy, not source authority.

## Quality Bar

A generated artifact is good when an agent can tell it is generated, knows not
to edit it by hand, and can find the owning source or command that rebuilds it.
