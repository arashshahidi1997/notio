# Maintain Indexes

## Rebuild all indexes

```bash
notio toc --all
```

## Rebuild one note-type index

```bash
notio toc meeting
```

## How indexes work

`notio` scans files under each configured note folder, reads simple frontmatter fields, and writes `index.md` files for:

- the note type, such as `docs/log/meeting/index.md`
- the root notes directory, such as `docs/log/index.md`

Indexes are refreshed automatically when you create notes through `notio note`.

