# Use the MCP Server

## Install

The MCP server requires the optional `mcp` dependency:

```bash
pip install notio[mcp]
```

## Start the server

```bash
notio mcp
```

Or with a specific project root:

```bash
notio --root /path/to/project mcp
```

The server runs over stdio using the FastMCP protocol.

## Available tools

Once running, agents can call:

| Tool | Description |
|------|-------------|
| `note_list` | List recent notes, optionally filtered by type |
| `note_latest` | Content of the most recent note |
| `note_read` | Read a specific note by path |
| `note_create` | Create a new note |
| `note_types` | List configured note types |
| `toc_rebuild` | Regenerate note indexes |
| `diataxis_init` | Scaffold Diataxis docs |
| `diataxis_add` | Add a page to a Diataxis section |
| `diataxis_toc` | Rebuild Diataxis section indexes |
| `config_show` | Show current configuration |

## Use as a library

The query functions are also available for direct import:

```python
from notio import list_notes, latest_note, read_note

notes = list_notes(".", note_type="idea", limit=5)
latest = latest_note(".", note_type="daily")
note = read_note(".", "docs/log/meeting/meeting-arash-20260312.md")
```

## Configure the root

The MCP server resolves the project root from:

1. The `--root` CLI flag (sets `NOTIO_ROOT` automatically)
2. The `NOTIO_ROOT` environment variable
3. The current working directory (fallback)
