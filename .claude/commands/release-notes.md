---
allowed-tools: Bash(git *), Read, Write, Edit, AskUserQuestion
description: (Command) Generates user-facing release notes from git history
---

# Release Notes Generator

You generate concise, user-facing release notes from git commit history, append them to `RELEASE_NOTES.md`, commit, and tag the release.

## Arguments

`$ARGUMENTS` — optional commit hash to use as the starting point (exclusive). If empty, auto-detect (see below).

## Workflow

### 1. Determine starting point

If `$ARGUMENTS` is provided, use it as the starting commit.

Otherwise, auto-detect:
- Run `git log -1 --format=%H -- RELEASE_NOTES.md` to find the last commit that touched the file.
- If that returns nothing (file doesn't exist yet), use `git log --reverse --format=%H | head -1` (the first commit in the repo).

### 2. Get commit list

Run `git log <start_hash>..HEAD --oneline` on the current branch to get the commit list.

### 3. Generate release notes

Analyze the commits and generate release notes following the format and rules below.

### 4. Suggest semver bump

Look at the latest git tag: `git describe --tags --abbrev=0 2>/dev/null` (defaults to `v0.0.0` if none).

Analyze the commits:
- **Breaking changes** → suggest **major** bump
- **New features** → suggest **minor** bump
- **Bug fixes / improvements only** → suggest **patch** bump

Show the suggestion and **ask the user** (via `AskUserQuestion`) to confirm or pick a different version.

### 5. Append to RELEASE_NOTES.md

Append the entry to `RELEASE_NOTES.md` (create the file if it doesn't exist). Use raw markdown — do NOT escape it in the file. Separate entries with a blank line.

### 6. Commit and tag

Run:
```
git add RELEASE_NOTES.md && git commit -m "Release vX.Y.Z"
git tag -a vX.Y.Z -m "Release vX.Y.Z"
```

**Important:** Always create an **annotated** tag (`-a`), not a lightweight one. `push.followTags` only follows annotated tags — lightweight tags require an explicit push and are easy to forget.

### 7. Push

**Important:** The tag MUST be pushed to GitHub — production uses `git describe --tags` to display the version. A missing tag causes the UI to show a commit hash instead of the semver.

Ask the user (via `AskUserQuestion`) whether they want:

1. **Claude pushes** — Run `git push && git push origin vX.Y.Z`
2. **I'll push manually** — Check `git config --get push.followTags`. If the output is `true`, tell the user they can simply run `git push` and the tag will be included automatically. If the output is anything else (empty/false), warn the user that their git config does NOT have `push.followTags` enabled, so they must run both commands: `git push && git push origin vX.Y.Z`. Suggest they enable it globally with `git config --global push.followTags true` to avoid this in future.

### 8. Output to terminal

Also output the escaped version to the terminal (as described in Output Format below) so the user can see what was generated.

## Entry Format (for RELEASE_NOTES.md)

Each entry uses this exact format (raw markdown, no escaping):
```
## What's new in vX.Y.Z — {DD MMM YYYY}
- **Bold title** description of the change in plain language
- **Another title** another description for users
```

- The heading includes the semver version and uses an em dash (`—`) with the date in `DD MMM YYYY` format
- Entries separated by a blank line
- No blank lines between list items within an entry

## Terminal Output Format

CRITICAL: Escape ALL markdown syntax with backslashes so characters render literally and are not parsed. For example:
- `\#\#` instead of `##`
- `\*\*bold\*\*` instead of `**bold**`
- `\*italics\*` instead of `*italics*`
- `\-` instead of `-` at the start of lines
- `` \` `` instead of `` ` `` around inline code

The user must see the raw markdown characters (`**`, `*`, `##`, `` ` ``, `-`) in your output, not rendered formatting.

## Rules

- CRITICAL: No blank lines between list items. No leading spaces before hyphens. Every `- ` line starts at column 0 with no indentation.
- Write 6-10 bullet points summarizing meaningful changes
- Each bullet: `- **Bold title** (1-4 words)` then a plain-English description (5-20 words)
- Use *italics* for UI elements and data/field names (e.g., *My Bookings*, *Start Date*)
- Use `backticks` for URLs, config values, and technical identifiers
- Group related commits into a single bullet when they address the same feature
- Skip: formatting-only changes, dependency updates, chores, CI config, refactors with no user impact
- Write for non-technical users — focus on what changed in the app, not how the code changed
- Use past tense ("Added", "Fixed", "Improved")
