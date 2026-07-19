---
name: statusline-config
description: Sets the style and features of Claude Code's status line.
---

Create a shell script at `~/.claude/statusline-command.sh` and register it in `~/.claude/settings.json` (statusLine.type: "command"). The script receives Claude Code's status JSON on stdin and prints a single line of pipe-separated (|) segments. Discover the exact JSON field names yourself from the current payload rather than assuming them — the schema evolves.

## Segments, left to right:

1. Working directory — the workspace's current directory, with a sensible fallback if that field is absent.
2. Git branch — detected from the working directory. Color it (red on the default/main branch, green elsewhere) and append a marker when the tree has uncommitted changes. Read git safely so a slow or locked repo can't stall the line, and degrade gracefully outside a repo or in unusual head states (freshly initialized, detached).
3. Model — the active model's display name.
4. Context usage — as a rounded percentage. Only show it once there's real usage data; hide it otherwise rather than printing a placeholder. Percentage should be of the model's actual context window, which may be larger than the default.
5. Session elapsed time — persisted per session so it survives status-line refreshes, formatted by magnitude (seconds → minutes+seconds → hours+minutes).

## Style & robustness:

- Every segment degrades independently: if one can't be computed, omit it and still print a clean line — never error out or leave dangling separators.
- Render colors with ANSI escapes and a printf that interprets them; always reset color at the segment's end.
- Assume nothing about optional tooling (e.g. jq) being present — check first and fall back if needed.
- Keep it fast; the line runs on every refresh.

## Target output shape:
/path/to/project | branch: dev | Claude Sonnet 4.6 | ctx 18% | 4m 32s

Verify by piping representative JSON payloads through the script before finishing: cover the default vs. a feature branch, clean vs. dirty tree, present vs. absent context data, a larger context window, and running outside a git repo.
