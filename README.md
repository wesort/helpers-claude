# helpers-claude

By Ben Edmonds, [wesort.co.uk](https://wesort.co.uk)

A canonical source for myself of reusable Claude Code commands and SKILLS. If you aren't me, [YMMV](https://www.google.com/search?q=ymmv).

Projects keep their own copies of commands — this repo is the
**reference/source of truth**. It is not a package or dependency.
Projects maintain their own command files and use `/check-helpers`
to see if the helpers repo has newer versions worth pulling in, or
if the project has local changes worth pushing upstream.

## What's Included

| Command | Description |
|---------|-------------|
| `/commit` | Guided commit workflow |
| `/plans` | Plan-mode workflow |
| `/release-notes` | Generate release notes | 
| `/check-helpers` | Compare project commands against this repo |
| ... and more |  |

## How It Works

This is not a package manager. The coupling between this repo and
any project is intentionally loose:

1. Each project keeps its own copy of command files in its
   `.claude/commands/` directory.
2. The `/check-helpers` command (run inside any project) compares
   timestamps and git commits to flag when the helpers repo or the
   project's commands have diverged.
3. You decide what to sync and when — nothing auto-syncs.
  here. Projects copy what they need.
- **Loosely coupled** — Checked via timestamps and git, never
  auto-synced.
- **Portable** — Commands make no project-specific assumptions
  about languages, frameworks, or directory structure.
