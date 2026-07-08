# Visible Body

Power: inspectability.

The agent's project body is visible, ordinary, and inspectable in the
repository.

Decision Question: does this belong in the visible project body, or in hidden
machinery?

## Law

Durable project memory lives in visible body folders:

- `context/`;
- `assets/`;
- `routines/`;
- `capabilities/`.

Hidden paths are for binding, configuration, generated output, local state, or
tool machinery. Legacy dot-body folders are migration inputs, not canonical
homes.

## Failure Signs

- durable doctrine lives only in a host-specific hidden surface;
- dot-body folders remain canonical after migration;
- generated host files are treated as the project body.
