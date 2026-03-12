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

