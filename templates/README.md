# Templates

Templates are optional starter files shipped by ContextKit.

They are gallery items, not doctrine for the ContextKit repository itself. A project can copy and adapt the project-body set during onboarding or initialization instead of inventing folder names and file shapes from scratch.

The manager reads `context/` when listing project templates or creating project starter files with template-enabled init, adopt, or bootstrap flows.

`context/` contains the project-body starter set used by `--with-template`. `global-context/` contains the separate global-context source starter used only by `contextkit global-context init`; it is never copied into a project by the project-template flows.
