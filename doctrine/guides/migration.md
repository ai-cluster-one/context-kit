# Migration Guide

Start with `contextkit migrate --plan`. Move live durable facts into `context/`,
preserve historical records under `assets/`, and replace host-specific generated
files only after the compiled ContextKit output matches the project semantics.
