# Set up a Claude Code status line.

Create a shell script at ~/.claude/statusline-command.sh and register it in
~/.claude/settings.json (statusLine.type: "command"). The script receives Claude
Code's status JSON on stdin and prints a single line of pipe-separated (|)
segments. Discover the exact JSON field names yourself from the current payload
rather than assuming them — the schema evolves.

## Segments, left to right:

1. Working directory — the workspace's current directory, abbreviating $HOME to
   ~, with a sensible fallback if that field is absent.
2. Git branch — detected from the working directory. Color it (red on the
   default/main branch, green elsewhere) and append a marker when the tree has
   uncommitted changes. Read git safely so a slow or locked repo can't stall the
   line, and degrade gracefully outside a repo or in unusual head states
   (freshly initialized, detached).
3. Model — the active model's display name.
4. Context usage — as a rounded percentage. Only show it once there's real usage
   data; hide it otherwise rather than printing a placeholder. Percentage should
   be of the model's actual context window, which may be larger than the default.
5. Session elapsed time — persisted per session so it survives status-line
   refreshes, formatted by magnitude (seconds → minutes+seconds → hours+minutes).
6. 5-hour rate-limit usage — the current 5-hour usage window as a rounded
   percentage, followed by its local-time reset ("@HH:MM").
7. 7-day rate-limit usage — the rolling 7-day usage as a rounded percentage,
   followed by its local reset ("@Day Mon D, HH:MM").

## Rate-limit segments (6 & 7) — sourcing and behavior:

This reference might be helpful: https://github.com/daniel3303/ClaudeCodeStatusLine/blob/main/statusline.sh

These come from Anthropic's usage data, which is NOT a documented part of the
status JSON contract — treat the whole feature as best-effort and make each
segment vanish cleanly whenever anything is missing or fails.

- Source order: first look for rate-limit fields already present in the piped
  status JSON and use them if found (no network call). Only if they're absent,
  fall back to the OAuth usage endpoint:
    GET https://api.anthropic.com/api/oauth/usage
    Headers: Authorization: Bearer <token>, anthropic-beta: oauth-2025-04-20
  The bearer token comes from $CLAUDE_CODE_OAUTH_TOKEN, else the
  .claudeAiOauth.accessToken field of
  ${CLAUDE_CONFIG_DIR:-$HOME/.claude}/.credentials.json. The response exposes a
  5-hour and a 7-day object, each with a usage percen
  timestamp.
- Cache the endpoint response to a temp file and refr
  seconds (mtime-based), so the line doesn't make a network call on every
  refresh. Guard against parallel panes racing (stamp
  fails, don't leave a stale/empty cache that suppresses retries.
- Bound the network call with a short curl timeout, a
  entirely — never error — if the token, tooling, or a valid response is missing.
- Reset timestamps may arrive as ISO-8601 (endpoint)
  JSON); convert either to local time.

## Color-coding the usage percentages (segments 6 & 7):

Color each rate-limit percentage by severity:
  < 50%  green   ·   50–70%  yellow   ·   70–90%  ora
Use the same "ANSI escape literal, rendered by a printf that interprets escapes"
convention as the rest of the line. Basic ANSI has no
code for it. Always reset color at the end of the segment.

## Style & robustness:

- Every segment degrades independently: if one can't be computed, omit it and
  still print a clean line — never error out or leave
- Render colors with ANSI escapes and a printf that interprets them; always
  reset color at the segment's end.
- Assume nothing about optional tooling (e.g. jq, curl) being present — check
  first and fall back or omit if absent.
- Keep it fast; the line runs on every refresh. The 60s cache is what keeps the
  rate-limit lookup cheap.

## Target output shape:

/path/to/project | branch: dev | Claude Sonnet 4.6 | :00 | 7d 19% @Thu Jul 23, 03:00

## Verify before finishing:

Pipe representative JSON payloads through the script
feature branch, clean vs. dirty tree, present vs. absent context data, a larger
context window, and running outside a git repo. For t
confirm: they append after the time segment; a cold cache triggers exactly one
endpoint fetch and a warm cache within 60s makes none
color-code across the green/yellow/orange/red thresholds; reset times render in
local time; and everything before the rate-limit segm
can't be produced (missing token, offline, no jq/curl).
