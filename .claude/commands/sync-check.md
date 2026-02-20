---
allowed-tools: Bash(git clone *), Bash(git -C /tmp/sync-check-clone *), Bash(git log *), Bash(find /tmp/sync-check-clone -delete), Glob, Read, AskUserQuestion
description: Compare local commands with a remote repo's .claude/commands/ directory
---

# Command Sync Checker

You compare the local `.claude/commands/` directory against a remote GitHub repository's `.claude/commands/` directory. You clone only the commands directory, diff against local copies, and produce an actionable sync report.

## Arguments

`$ARGUMENTS` — optional GitHub repository URL or slug (e.g., `https://github.com/owner/repo`, `owner/repo`). If empty, prompt the user via `AskUserQuestion`.

## Workflow

### 1. Resolve the target repository

If `$ARGUMENTS` is provided, extract the `owner/repo` slug. Accept any of these formats:
- `https://github.com/owner/repo`
- `https://github.com/owner/repo.git`
- `github.com/owner/repo`
- `owner/repo`

If `$ARGUMENTS` is empty, ask the user via `AskUserQuestion`:
- Question: "Which GitHub repository should I compare against?"
- Provide an "Other" option so they can paste a URL or slug.

### 2. Clone the remote commands directory

Blobless clone (`--filter=blob:none`) with sparse checkout via SSH.
This fetches full commit history (needed for accurate per-file dates)
but only downloads blob content for `.claude/commands/`.

**IMPORTANT:** Run each command as a separate Bash call so they match the `allowed-tools` patterns and auto-approve. Do NOT chain them with `&&`.

The clone target is always `/tmp/sync-check-clone`. Remove it first if it exists from a previous run, then clone:

1. Clean any previous run:
   ```
   find /tmp/sync-check-clone -delete
   ```

2. Clone into it:
   ```
   git clone --filter=blob:none --sparse git@github.com:{owner}/{repo}.git /tmp/sync-check-clone
   ```

3. Set sparse checkout:
   ```
   git -C /tmp/sync-check-clone sparse-checkout set .claude/commands
   ```

If the clone fails, report the error clearly and advise the user to check their SSH key configuration (`ssh -T git@github.com`) and stop.

If `/tmp/sync-check-clone/.claude/commands/` does not exist or contains no `.md` files, report that the remote repo has no `.claude/commands/` directory, clean up, and stop.

### 3. Read remote file contents

List all `.md` files in `/tmp/sync-check-clone/.claude/commands/` and use `Read` to get each file's contents. Store them for comparison.

### 4. Fetch remote git history for commands

Get the last-modified date for each remote `.md` file:
```
git -C /tmp/sync-check-clone log -1 --format='%ad' --date=format:'%d %b %Y %H:%M' -- .claude/commands/{filename}
```

For per-file commit history when needed (e.g., for Remote Only or Diverged):
```
git -C /tmp/sync-check-clone log --oneline -5 -- .claude/commands/{filename}
```

### 5. Read local command inventory

Use `Glob` to find all `.md` files in `.claude/commands/` relative to the current working directory.

For each local file found, use `Read` to get its contents. Also get
the last-modified date from git:
```
git log -1 --format='%ad' --date=format:'%d %b %Y %H:%M' -- .claude/commands/{filename}
```

### 6. Compare and classify

Classify every command file into one of four categories:

- **Remote only** — exists in remote but not locally. Candidate for adoption.
- **Local only** — exists locally but not in remote. Unique to this project.
- **Identical** — exists in both and content matches exactly.
- **Diverged** — exists in both but content differs.

For diverged files, identify the nature of the differences:
- Frontmatter changes (allowed-tools, description)
- Structural changes (new/removed/reordered sections)
- Content changes (wording, rules, examples)

### 7. Clean up

Remove the temporary directory:
```
find /tmp/sync-check-clone -delete
```

### 8. Produce the report

Output the report. The banner MUST be inside a single fenced
code block so the terminal preserves the box drawing exactly. Section
tables that follow use normal markdown outside the code block.

**Banner** (inside a fenced code block):
```
  +----------------------------------------------------+
  |                                                    |
  |   Sync Report: {owner}/{repo}                     |
  |                                                    |
  |   {remote} remote  {local} local                  |
  |   [=] {identical} identical  [!] {diverged} diverged  |
  |   [+] {remote_only} remote only  [~] {local_only} local only  |
  |                                                    |
  +----------------------------------------------------+
```

Right-pad each line inside the box so the `|` characters align
flush on the right edge. Omit any counter line that is zero.

**Sections** (normal markdown, outside the code block):

Use these ASCII markers instead of emoji in headings:

- `[+]` for Remote Only
- `[!]` for Diverged
- `[~]` for Local Only
- `[=]` for Identical

```
  --- [+] Remote Only -- candidates to adopt -----------

  | Command | Description | Local Modified | Remote Modified | Last Commit |
  |---------|-------------|----------------|-----------------|-------------|
  | `name`  | frontmatter |                | 30 Jan 2026 14:35 | msg |

  --- [!] Diverged -- review recommended ---------------

  | Command | Description | Local Modified | Remote Modified | Differences |
  |---------|-------------|----------------|-----------------|-------------|
  | `name`  | frontmatter | 30 Jan 2026 14:35 | 02 Feb 2026 09:12 | summary |

  --- [~] Local Only -- unique to this project ---------

  | Command | Description | Local Modified | Remote Modified |
  |---------|-------------|----------------|-----------------|
  | `name`  | frontmatter | 30 Jan 2026 14:35 |                 |

  --- [=] Identical -- no action needed ----------------

  | Command | Description | Local Modified | Remote Modified |
  |---------|-------------|----------------|-----------------|
  | `name`  | frontmatter | 30 Jan 2026 14:35 | 02 Feb 2026 09:12 |
```

The `---` section dividers are plain text, not markdown horizontal
rules. Output them literally with the dashes and label.

**Date columns:**
All sections use **Local Modified** and **Remote Modified** columns.
Both use `git log -1` author dates from their respective repos.
Filesystem mtime is not used because git does not preserve it —
any checkout, pull, or clone resets mtime to the current time.
Leave a cell blank when the file does not exist on that side
(Remote Only → no local date; Local Only → no remote date).
For Identical files, both dates are shown so the user can see
whether the local copy is older or newer than the remote.

Omit any section that has zero entries. Omit counts of zero from
the banner.

## Rules

- Do NOT modify any local files. This command is read-only.
- Use a blobless sparse clone to minimize bandwidth. Always clean up the temp directory when done.
- If the clone fails due to authentication or access, report the error clearly and stop.
- Keep the diff summaries concise — highlight what changed, not the full diff.
- When a command is diverged, do NOT recommend one version over the other. Present the differences neutrally and let the user decide.
