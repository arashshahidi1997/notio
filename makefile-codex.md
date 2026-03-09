# Makefile + agentic AI (short note)

For agentic AI work, a `Makefile` can act like a **safe, discoverable command menu**. An AI assistant can read the target names (or run `make help`) to quickly understand what the project supports, *without guessing* which scripts to run or where files live.

## Why this helps

- **Fast project overview**: targets communicate the workflow (“how we create notes”, “how we update indexes”, “how we format”, “how we test”).
- **Less guesswork**: the Makefile encodes paths + flags, so the agent doesn’t invent commands.
- **Repeatable actions**: the same target does the same thing every time (good for humans *and* AI).

## Example “AI-friendly” targets (imagined)

If your Makefile exposes targets like these:

- `make note-script NAME="slug"` — create a note stub in the right folder from a template.
- `make note-fill FILE="docs/..."` — open/update a specific note (or validate required sections).
- `make commit MSG="..."` — run checks, then create a git commit with a message.

…then after writing a script, an agent can follow the project’s workflow by running the same named targets a human would.

## Tiny workflow example

```bash
make note-script NAME="my-new-script"
# (agent writes the script + fills the generated note)
make commit MSG="Add my-new-script and documentation note"
```

