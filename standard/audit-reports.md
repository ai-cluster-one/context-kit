# Audit Reports Standard

Rule source for audit walks, findings, and persisted audit reports.

## Contract

An audit report identifies the project, the audit procedure, and each finding's
severity, affected path, rule source, observed problem, owning source to edit,
recommended repair, and repair mode.

Finding severities are:

- error: structure, metadata, or binding prevents compilation or reliable
  routing;
- warning: drift, duplicate truth, wrong altitude, unsafe placement, or
  rule-source violation is likely;
- info: taxonomy or quality hint for human review.

Cross-layer findings name each violated owner. A report repairs source truth,
not generated output.

## Quality Bar

An audit report is good when every finding can be followed to the rule source
that owns the repair, and accepted warnings have an explicit owner for the
exception.
