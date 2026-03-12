# Project Model

`notio` assumes each project owns its own note workspace.

That workspace has three parts:

1. Configuration, usually `notio.toml`
2. Templates, usually `.notio/templates/`
3. Rendered notes and indexes, usually `docs/log/`

The important boundary is that behavior belongs in configuration and templates, not in shell scripts or Make rules.

This lets one package serve many repositories with different note types and conventions.

