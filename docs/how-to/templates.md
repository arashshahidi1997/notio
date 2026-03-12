# Customize Templates

Templates live under `.notio/templates/`.

They are plain text files rendered with Python `string.Template`.

## Example template

```md
---
title: "${title}"
date: ${date}
timestamp: ${timestamp}
tags: [meeting]
---

# ${title} - ${date}

## Notes
- 
```

## Available variables

- `${title}`
- `${owner}`
- `${date}`
- `${timestamp}`
- `${year}`
- `${month}`
- `${day}`
- `${week}`

Compatibility variables are also available for old Foam-style templates:

- `${FOAM_TITLE}`
- `${FOAM_DATE_YEAR}`
- `${FOAM_DATE_MONTH}`
- `${FOAM_DATE_DATE}`
- `${FOAM_DATE_WEEK}`
- `${FOAM_TIMESTAMP}`

