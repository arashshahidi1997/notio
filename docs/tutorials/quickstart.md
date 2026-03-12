# Quickstart

This walkthrough starts from an empty project and turns it into a `notio` workspace.

## 1. Install `notio`

From a checkout:

```bash
pip install .
```

Or for local development without installation:

```bash
PYTHONPATH=src /storage/share/python/environments/Anaconda3/envs/labpy/bin/python -m notio --root . --version
```

## 2. Initialize a workspace

```bash
notio init --write-config
```

This creates:

- `notio.toml`
- `.notio/templates/`
- `docs/log/`
- `docs/log/<type>/index.md`

## 3. Create a note

```bash
notio note meeting --title "Sprint sync"
```

This writes a timestamped meeting note and refreshes:

- `docs/log/meeting/index.md`
- `docs/log/index.md`

## 4. Create a period note

```bash
notio note daily
notio note weekly
```

These write stable files based on the configured date/week pattern.

## 5. Rebuild indexes explicitly

```bash
notio toc --all
```

