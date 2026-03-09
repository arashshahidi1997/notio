# Makefile usage (short demo)

A `Makefile` is a tiny “command menu” for your project: it gives names to common actions and records *how* to run them (which tool, which folder, which arguments). Instead of relying on memory (or scattered shell history), collaborators can type `make help` and immediately see what the project supports.

## What a Makefile helps with (any project)

- **Onboarding & collaboration**: one place to discover the “official” commands (`make help`).
- **After a break**: quickly remember procedures (“how do I regenerate indexes?”, “how do I create today’s note?”).
- **Correct context**: targets run the right tool with the right inputs from the right place.
- **Repeatability**: same command name means the same action every time.

## In this `makenotes/` demo

From the `makenotes/` folder you can run:

- `make help` — list available commands and overrides.
- `make note-daily` / `make note-weekly` — create/update period notes in `docs/log/`.
- `make note-issue TITLE="..."` (and other `note-<type>`) — create timestamped event notes from templates.
- `make toc-all` — regenerate `docs/log/<type>/index.md` navigation files.

## Simple example (memory vs Makefile)

Without a Makefile, you might need to remember something like:

1) “Go to the right folder”
2) “Run the right script with the right arguments”

For example:

```bash
cd docs/log/issue
python3 ../../../code/scripts/toc-index.py . issue status groupby=status
```

With the Makefile, you just run:

```bash
make toc-issue
```

The Makefile “remembers” the script path, the folder, and the arguments so you don’t have to.

