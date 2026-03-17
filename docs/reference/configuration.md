# Configuration

`notio` reads configuration from:

- `notio.toml`
- `[tool.notio]` in `pyproject.toml`

`notio.toml` takes precedence.

## Example

```toml
version = 1
notes_root = "docs/log"
template_root = ".notio/templates"

[types.daily]
mode = "period"
template = "daily.md"
filename = "daily-{owner}-{date}.md"

[types.issue]
mode = "event"
template = "issue.md"
filename = "issue-{owner}-{timestamp}.md"
toc_keys = ["status"]
toc_groupby = "status"
```

## Top-level fields

- `version`
- `notes_root`
- `template_root`

## Per-type fields

- `mode`
- `template`
- `filename`
- `toc_keys`
- `toc_groupby`

### Task note type

The built-in `task` type supports the workflow pipeline's "decide" stage — promoting ideas into executable work items:

```toml
[types.task]
mode = "event"
template = "task.md"
filename = "task-{owner}-{timestamp}.md"
toc_keys = ["status", "title"]
toc_groupby = "status"
```

Task notes include frontmatter fields for `status` (pending/active/done/cancelled), `actionable`, `prompt` (agent instruction), and `source_note` (link to the originating note). The `--enrich` flag generates a structured Prompt section from source content via LLM.

## Diataxis section

The optional `[diataxis]` section configures the Diataxis documentation scaffolding.

```toml
[diataxis]
docs_root = "docs"
sections = ["tutorials", "how-to", "explanation", "reference"]
```

- `docs_root`: directory for documentation output (default `"docs"`)
- `sections`: list of Diataxis sections to manage (default: all four standard sections)

When omitted, `notio diataxis` commands use the defaults above.

## MCP dependencies

The MCP server is an optional feature. Install with:

```bash
pip install notio[mcp]
```

This pulls in `fastmcp` as a dependency.

## Environment variables

- `NOTIO_ROOT`: project root for the MCP server (default: current directory). Set automatically when using `notio mcp --root <path>`.

