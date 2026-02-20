# CLAUDE.md

## Project Context

Library of canonical Claude Code slash commands. Plain markdown
files — no build tools, no runtime dependencies.

## Repo Structure

- `.claude/commands/` — Slash command markdown files
- `README.md` — Purpose, structure, how the loose coupling works
- `CLAUDE.md` — This file; conventions for working in this repo

## Command Writing Conventions

- YAML frontmatter is required. Include `allowed-tools` and
  `description` at minimum.
- Commands must be portable — no hardcoded project paths, no
  framework or language assumptions.
- Use `$ARGUMENTS` for user input. Document expected arguments in
  an `## Arguments` section.
- Structure: single `# Title`, then `## Sections` for workflow
  steps, rules, and output format.
- Keep `allowed-tools` minimal — only request the permissions the
  command actually needs.

## Commit Messages

Follow Chris Beams rules:

- Imperative subject line, 50 characters or less
- Blank line between subject and body
- Wrap body at 72 characters
- Use the body to explain *what* and *why*, not *how*

## What Not to Do

- No project-specific commands — commands here must work in any
  project.
- No framework or language dependencies — commands are plain
  markdown consumed by Claude Code.
- No auto-sync mechanisms — loose coupling is enforced by design.
