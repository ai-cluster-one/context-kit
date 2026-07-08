# Generated Output

Power: reproducible projection.

Generated files are delivery artifacts, not authored truth.

Decision Question: is this artifact an authored source, or a downstream
projection produced for a host, build, or moment?

## Law

A generated file has one writer: the generator that owns it.

Generated output may be inspected to verify delivery, parity, and runtime
shape. It is not patched as the repair path. When generated output is wrong,
repair the owning source and rebuild.

Runtime visibility does not create source authority.

## Failure Signs

- generated files are manually edited;
- two generators write the same target;
- host-specific generated output contains unique source facts.
