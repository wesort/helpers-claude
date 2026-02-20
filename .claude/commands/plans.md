---
allowed-tools: Glob, Grep, Read, Bash, AskUserQuestion
description: List saved plan files
---

# List Plans

1. Run this Bash command to get the 10 most recently modified plan files with their dates:
   ```
   stat --format='%Y %y %n' ~/.claude/plans/*.md 2>/dev/null | sort -rn | head -10 | awk '{split($2,d,"-"); print d[1]"-"d[2]"-"d[3], $NF}'
   ```
   This gives pairs of `YYYY-MM-DD /full/path` sorted by most recent first.

2. For each file, use Grep to extract the first `# ` heading line as the title.

3. Display the results as a numbered markdown table with columns: **#**, **Date**, **Filename** (without path/extension), **Title**. Most recent first.

4. Ask the user to pick a plan by number using AskUserQuestion. List the first 4 plans as options (label: "#1 — Title", description: filename). The user can also type a number or name via "Other".

5. When the user selects a plan, use Read to display the full plan contents.
