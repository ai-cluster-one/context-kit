# README And CLI Standard

Rule source for human repository orientation and executable command surfaces.

## README Contract

A README orients a human reader. It explains what ContextKit is, what the user
gets, how to start, how the project body is shaped, and where to find command
truth. It does not become the complete command contract or implementation
manual.

## CLI Contract

The CLI owns exact command names, flags, effects, output shapes, and current
readiness checks. Product prose may show common examples and route to help, but
the live executable surface answers command-answerable questions.

## Quality Bar

README prose is good when a human can begin safely. CLI help is good when an
agent can discover exact syntax and current behavior at use time.
