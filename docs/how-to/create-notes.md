# Create Notes

## Create an event note

```bash
notio note meeting --title "Sprint sync"
notio note issue --title "Fix index grouping"
notio note idea --title "Add slug normalization"
```

Event notes use timestamped filenames by default.

## Create a period note

```bash
notio note daily
notio note weekly --date 2026-03-09
```

Period notes map to a stable filename pattern for the configured period.

## Override owner or timestamp

```bash
notio note meeting --owner arash --timestamp 20260309-190000-000001 --title "Review"
```

## Force overwrite

```bash
notio note daily --force
```

