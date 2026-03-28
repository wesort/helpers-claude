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

### 3. Pre-release risk assessment

Review the commits from step 2 and the actual diffs (`git diff <start>..HEAD`) to assess deployment readiness. Present a terse summary using this format:

**Risky changes:**
- `{file or area}` — {one-line issue} → {suggested fix or action}
- (or "None found")

**Testing gaps:**
- Run `php artisan test --compact` (full suite) and report pass/fail count
- Flag any commits that lack test coverage for non-trivial logic
- Suggest specific manual QA checks if automated tests can't cover it (e.g., visual UI changes, Airtable sync interactions)
- (or "All changes have adequate test coverage")

**Deploy script / CI/CD:**
- Flag if any commits add new artisan commands, migrations, env vars, npm dependencies, or config changes that need deploy script updates
- Reference the deploy steps in `docs/deployment.md` lines 245-267
- (or "No deploy script changes needed")

**User-facing breaking changes:**
- Flag changed routes (may need redirects), removed features, or changed permissions
- UI refactors are OK — only flag if URLs, navigation, or workflows changed
- Ask the user about any flagged items via `AskUserQuestion`
- (or "No breaking changes")

**Gaps / edge cases / hacks:**
- Flag TODOs, hardcoded values, missing error handling at system boundaries, or workarounds introduced in this release
- (or "None found")

**Dependency maintenance:**
- Check when `composer.lock` and `package-lock.json` were last updated: `git log -1 --format=%ai -- composer.lock` and `git log -1 --format=%ai -- package-lock.json`
- If either file hasn't been updated in 30+ days, flag it with a suggestion to run `composer update` / `npm update` before release
- (or "Dependencies are up to date")

After presenting the assessment, ask the user (via `AskUserQuestion`): "Proceed with release, or address issues first?"
- If "address first" → stop and let the user fix things
- If "proceed" → continue to step 4

### 4. Check if case study needs updating

Before generating release notes, review the commit list and ask the user whether the public case study page (`/case-study`) needs updating to reflect this release — e.g., updated stats, a new phase, revised dates, or new features worth highlighting. The content lives in `resources/views/partials/case-study-body.blade.php`. If updates are needed, make them before proceeding so they're included in the release commit.

### 5. Generate release notes

Analyze the commits and generate release notes following the format and rules below.

### 6. Suggest semver bump

Look at the latest git tag: `git describe --tags --abbrev=0 2>/dev/null` (defaults to `v0.0.0` if none).

Analyze the commits:
- **Breaking changes** → suggest **major** bump
- **New features** → suggest **minor** bump
- **Bug fixes / improvements only** → suggest **patch** bump

Show the suggestion and **ask the user** (via `AskUserQuestion`) to confirm or pick a different version.

### 7. Append to RELEASE_NOTES.md

Append the entry to `RELEASE_NOTES.md` (create the file if it doesn't exist). Use raw markdown — do NOT escape it in the file. Separate entries with a blank line.

### 8. Commit and tag

Run:
```
git add RELEASE_NOTES.md && git commit -m "Release vX.Y.Z"
git tag -a vX.Y.Z -m "Release vX.Y.Z"
```

**Important:** Always create an **annotated** tag (`-a`), not a lightweight one. `push.followTags` only follows annotated tags — lightweight tags require an explicit push and are easy to forget.

### 9. Output to terminal

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

### 10. Check if CLAUDE.md needs updating (optional)

After generating and committing release notes, scan the commits included in this release for signals that `CLAUDE.md` may need updating:
- New directories or architectural patterns introduced
- New enums, middleware, policies, or services added
- Changed conventions (e.g., new validation approach, new UI pattern)

If any signals are found:
1. Output a brief summary of what changed
2. Draft specific `CLAUDE.md` edits (as a diff or before/after) for the user to review
3. Ask the user (via `AskUserQuestion`) whether to apply the changes, skip, or modify
4. If approved, apply the edits and amend the release commit to include them

If no signals are found, skip this step silently.

## Rules

- CRITICAL: **NEVER** use the `Write` tool on RELEASE_NOTES.md — it overwrites the entire file. Always use `Read` then `Edit` to append new entries.
- CRITICAL: No blank lines between list items. No leading spaces before hyphens. Every `- ` line starts at column 0 with no indentation.
- Write 6-10 bullet points summarizing meaningful changes
- Each bullet: `- **Bold title** (1-4 words)` then a plain-English description (5-20 words)
- Use *italics* for UI elements and data/field names (e.g., *My Bookings*, *Start Date*)
- Use `backticks` for URLs, config values, and technical identifiers
- Group related commits into a single bullet when they address the same feature
- Skip: formatting-only changes, dependency updates, chores, CI config, refactors with no user impact, case study page updates
- Write for non-technical users — focus on what changed in the app, not how the code changed
- Use past tense ("Added", "Fixed", "Improved")
