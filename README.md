# helpers-claude

By Ben Edmonds, [wesort.co.uk](https://wesort.co.uk)

A canonical source for myself of reusable Claude Code commands and SKILLS. If you aren't me, [YMMV](https://www.google.com/search?q=ymmv).

Projects keep their own copies of commands — this repo is the
**reference/source of truth**. It is not a package or dependency.
Projects maintain their own command files and use `/sync-check`
to see if the helpers repo has newer versions worth pulling in, or
if the project has local changes worth pushing upstream.

## What's Included

| Command | Description |
|---------|-------------|
| `/commit` | Guided commit workflow |
| `/plans` | List saved plan files |
| `/release-notes` | Generate user-facing release notes from git history |
| `/docs` | Audit documentation against the codebase and suggest updates |
| `/sync-check` | Compare project commands against this repo |
| `/grill-me` | Stress-test a plan or design, one question at a time |
| `/grill-me-brand` | Sharpen a business's brand into a one-page brand core |
| `/triage` | Decide whether, how small, and when to build a piece of software |
| `/server-audit` | Read-only, no-sudo stack health and EOL/CVE audit of a server |
| `/statamic-upgrade-readiness` | Read-only audit of a Statamic site's route to Laravel 13 + Statamic 6 |
| `/statusline-config` | Set the style and features of Claude Code's status line |

## Install

Paste this into Claude Code from the root of the target project:

```text
Install my helpers into this repo from https://github.com/wesort/helpers-claude

1. Shallow-clone it into your scratchpad (or a temp dir) over SSH:
   git clone --depth 1 git@github.com:wesort/helpers-claude.git
   Fall back to HTTPS if SSH isn't set up.
2. Copy every .claude/commands/*.md into this project's
   .claude/commands/ (create it if missing). If a file already exists
   here and differs, don't overwrite it — list it and ask me.
3. Make sure .claude/settings.local.json is in .gitignore, so only
   the shared commands get committed.
4. Report what was installed, the helpers commit it came from, and
   flag any command that doesn't fit this project (wrong stack,
   needs a tool that isn't available here, etc).
5. Don't commit until I ask. When I do, commit only
   .claude/commands/ and .gitignore.
6. Delete the clone when done.
```

Afterwards, run `/sync-check wesort/helpers-claude` in the project to
see what has drifted.

## How It Works

This is not a package manager. The coupling between this repo and
any project is intentionally loose:

1. Each project keeps its own copy of command files in its
   `.claude/commands/` directory.
2. The `/sync-check` command (run inside any project) compares
   git commit dates and file contents to flag when the helpers repo
   or the project's commands have diverged.
3. You decide what to sync and when — nothing auto-syncs.

- **Loosely coupled** — Checked via git, never auto-synced.
  Projects copy what they need.
- **Portable** — Commands make no project-specific assumptions
  about languages, frameworks, or directory structure.
