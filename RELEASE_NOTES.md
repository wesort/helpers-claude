## What's new in v0.1.0 — 20 Feb 2026
- **Initial release** Canonical source of reusable Claude Code slash commands
- **Commit command** Guided git commit workflow with Chris Beams-style messages
- **Plans command** Lists and displays saved plan files from `~/.claude/plans/`
- **Release notes command** Generates user-facing release notes from git history, commits, and tags
- **Portable by design** All commands are framework- and language-agnostic markdown files
- **Loose coupling** Projects keep their own copies; nothing auto-syncs

## What's new in v0.1.1 — 20 Feb 2026
- **Sync-check command** Added `/sync-check` to compare local commands against a remote repo and report differences
- **Commands moved** Relocated commands to `.claude/commands/` so Claude Code auto-discovers them as slash commands
- **Renamed release-notes** Changed `release-note.md` to `release-notes.md` to match remote naming convention

## What's new in v0.1.2 — 20 Feb 2026
- **Clearer sync dates** Sync-check report now shows separate *Local Modified* and *Remote Modified* columns instead of one ambiguous *Modified* column
- **Annotated tags** Release notes command now creates annotated tags (`git tag -a`) so `push.followTags` works reliably
