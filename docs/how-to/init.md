# Initialize A Workspace

## Write a default config and scaffold the workspace

```bash
notio init --write-config
```

## Recreate default templates

```bash
notio init --force
```

Use this when you want to restore the shipped template set under `.notio/templates/`.

## Initialize a different repo

```bash
notio --root /path/to/project init --write-config
```

