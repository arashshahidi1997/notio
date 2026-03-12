# Workspace Layout

Default layout:

```text
project/
  notio.toml
  .notio/
    templates/
      daily.md
      weekly.md
      meeting.md
      issue.md
  docs/
    log/
      index.md
      daily/
        index.md
        daily-<owner>-<date>.md
      meeting/
        index.md
        meeting-<owner>-<timestamp>.md
```

The exact paths are configurable, but this is the default model `notio` scaffolds.

## Diataxis layout

Running `notio diataxis init` adds:

```text
project/
  docs/
    index.md
    tutorials/
      index.md
    how-to/
      index.md
    explanation/
      index.md
    reference/
      index.md
```

Pages added with `notio diataxis add` appear within the appropriate section directory.

