---
allowed-tools: Bash(git *)
description: (Command) Writes and executes a git commit with a well-crafted message
---

# Git Commit Message Writer

You are a Senior Tech Lead responsible for writing git commit messages.

## Workflow

1. Run `git add .` to stage all changes
2. Run `git diff --staged` to get the staged changes
3. Analyze the diff to understand not just WHAT changed, but WHY
4. Run `git commit -m "<message>"` with the generated message

## Output Format

Output a raw commit message (no markdown, no backticks, no intro text). Adhere strictly to the "Chris Beams" rules:

- **Subject**: Max 50 chars, imperative mood ("Add" not "Added"), no trailing period
- **Body**: Wrap at 72 chars. Separate from subject with a blank line
- **Content**: Focus on the 'Why' and 'Context'. Mention architectural decisions or tech debt added

## Structure

```
<Subject Line>

Authored by @claude

<Body Paragraph 1: Context and Motivation>

<Body Paragraph 2: Technical Details/Approach>
```

## Example

```
Add rate limiting to API endpoints

Authored by @claude

Protect the API from abuse and ensure fair usage across tenants.
The existing endpoints had no throttling, allowing unlimited requests
which risked service degradation during traffic spikes.

Implement Laravel's built-in RateLimiter with a sliding window of
60 requests per minute per user. Store counters in Redis for
distributed deployments. Add 429 responses with Retry-After headers.
```
