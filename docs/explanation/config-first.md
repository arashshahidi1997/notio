# Why Config-First

The original note system encoded note types, filenames, destinations, and TOC behavior directly in Makefiles.

That works inside one repository, but it does not scale cleanly across many projects.

`notio` moves that policy into `notio.toml` so that:

- projects can customize behavior without editing Python code
- Make wrappers can stay thin and optional
- a package install is sufficient to reuse the tool elsewhere

