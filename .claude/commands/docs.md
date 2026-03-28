---
allowed-tools: Read, Glob, Grep, Agent, Bash(php artisan route:list *), Bash(git log *), Bash(git diff *), Bash(ls *), Bash(wc *), Bash(stat *), mcp__laravel-boost__list-routes, mcp__laravel-boost__list-artisan-commands, mcp__laravel-boost__database-schema
description: (Command) Audits documentation against the codebase and suggests updates
---

# Documentation Auditor

You audit the project's documentation files against the actual codebase and surface discrete, actionable suggestions for keeping docs accurate.

## Arguments

`$ARGUMENTS` — optional. Can be:
- A file path or partial filename (e.g., `README.md`, `devs.md`, `docs/deployment.md`) — audit only that file
- A directory (e.g., `docs/about`) — audit all `.md` files in that directory
- Empty — full audit of all discovered documentation files

## Workflow

### 1. Discover documentation files

Find all markdown files to audit. If `$ARGUMENTS` specifies a file or directory, use that scope.

Otherwise, auto-discover by collecting:
1. Root-level doc files: glob for `*.md` in the project root (e.g., `README.md`, `CLAUDE.md`, `CONTRIBUTING.md`, `CHANGELOG.md`)
2. `docs/**/*.md` — everything under a `docs/` directory, recursively
3. Exclude: `vendor/`, `node_modules/`, `storage/`, `RELEASE_NOTES.md`, any file that is clearly not documentation (e.g., package changelogs)

If `$ARGUMENTS` is a partial filename (e.g., `devs.md`), match it against discovered files. If multiple files match, audit all matches.

Report the discovered file list and count before proceeding.

### 2. Explore the codebase

Launch up to 3 parallel Explore agents scanning non-overlapping domains. Each agent should return a structured inventory of what it finds.

**Agent 1 — Routes, middleware, auth:**
- Use the `mcp__laravel-boost__list-routes` MCP tool to get all registered routes (if available, otherwise `php artisan route:list --json`)
- Check `bootstrap/app.php` for middleware aliases and groups
- Check `app/Http/Middleware/` for custom middleware classes
- Check auth-related config (`config/fortify.php`, `config/auth.php`, etc.)
- List all route names, their URIs, middleware stacks, and controller/component targets

**Agent 2 — Models, services, enums, policies, commands:**
- Use `mcp__laravel-boost__list-artisan-commands` to get all artisan commands (if available)
- Use `mcp__laravel-boost__database-schema` to get table structures (if available)
- Glob for models (`app/Models/*.php`), services (`app/Services/**/*.php`), enums (`app/Enums/*.php`), policies (`app/Policies/*.php`)
- List class names, key methods, and relationships

**Agent 3 — Livewire components, config, scheduled tasks:**
- Glob for Livewire components (`app/Livewire/**/*.php`) and their Blade views (`resources/views/livewire/**/*.blade.php`)
- Check `routes/console.php` for scheduled tasks
- Check `config/*.php` for app-specific configuration
- List component names, their routes (if routable), and key features

If an MCP tool is not available, the agent should fall back to artisan commands or file-based exploration. If a directory doesn't exist (e.g., no `app/Livewire/`), skip it silently — don't report missing directories as findings.

### 3. Read all target documentation files

Read every doc file in scope. In parallel, get the last-modified date for each via:
```
git log -1 --format='%ad' --date=format:'%d %b %Y' -- {filepath}
```

### 4. Cross-reference and classify findings

Compare the codebase inventory against what each doc file says. Classify every finding into exactly one of four categories:

- **`[STALE]`** — Information in the doc that is outdated or wrong
  - Renamed or removed routes, classes, methods, or config keys
  - Wrong middleware names or stacks
  - Incorrect enum values or method signatures
  - Referenced files or paths that no longer exist
  - Outdated version numbers, dependencies, or setup instructions

- **`[MISSING]`** — Codebase features not documented anywhere in the audited files
  - New components, enums, services, policies, or artisan commands
  - New routes or middleware not mentioned in docs
  - New config keys or settings
  - New user-facing features with no doc coverage

- **`[INCONSISTENT]`** — The same thing described differently across docs
  - Conflicting route paths or names
  - Different descriptions of the same feature
  - Contradictory instructions or rules
  - Terminology used differently across files

- **`[GAP]`** — Feature is documented in one file but missing from another file where it's relevant
  - Infer each file's scope from its content and filename (e.g., a file about admin features, a file about deployment, an AI-facing guide)
  - A feature covered in a general architecture doc but absent from a user-facing guide that describes the same area
  - A convention documented in `CLAUDE.md` but not reflected in a developer guide, or vice versa
  - Do NOT flag gaps where the omission is clearly intentional (e.g., a fitter guide omitting admin-only features)

### 5. Present the report

Output a banner with counts, then numbered suggestions grouped by category.

**Banner** (inside a fenced code block):
```
  +----------------------------------------------------+
  |                                                    |
  |   Documentation Audit Report                      |
  |                                                    |
  |   {n} files audited    {date}                     |
  |   [!] {stale} stale  [+] {missing} missing       |
  |   [~] {inconsistent} inconsistent  [-] {gap} gaps |
  |                                                    |
  +----------------------------------------------------+
```

Right-pad each line so the `|` characters align flush on the right edge. Omit any counter line where all values are zero.

**Sections** (normal markdown, outside the code block):

```
--- [!] Stale — outdated information ----------------------

1. **{file}** — {what is wrong}
   Fix: {specific suggested change}

2. **{file}** — {what is wrong}
   Fix: {specific suggested change}

--- [+] Missing — undocumented features -------------------

3. **{file}** — {what is missing}
   Add: {what to add and where}

--- [~] Inconsistent — cross-doc conflicts ----------------

5. **{file1}** vs **{file2}** — {what conflicts}
   Fix: {which version is correct and what to change}

--- [-] Gaps — coverage gaps across files -----------------

7. **{file}** — {feature documented elsewhere but missing here}
   Add: {what to add, referencing the file where it is documented}
```

Use these ASCII markers in section headings (no emoji):
- `[!]` for Stale
- `[+]` for Missing
- `[~]` for Inconsistent
- `[-]` for Gaps

Omit any section that has zero entries. Number suggestions continuously across sections.

Each suggestion must be **discrete and actionable** — a single, specific thing to fix in a specific file. Never suggest "rewrite this section" or "update this file generally."

### 6. Q&A

After presenting the report, ask the user which items they'd like to address. Discuss priorities, clarify findings, and get feedback. Do NOT auto-apply any changes — Edit and Write are not in allowed-tools, so any fix requires explicit user approval.

## Rules

- **Read-only.** Do NOT modify any files. Edit and Write are intentionally excluded from allowed-tools.
- **Discrete suggestions.** Each finding is one numbered item with a target file and specific fix. No vague "review this area" suggestions.
- **No false positives.** Only report findings you are confident about. If unsure whether something is stale or just undocumented by design, skip it or flag the uncertainty.
- **Respect existing structure.** Suggestions should fit the existing doc format and tone. Don't propose restructuring entire files.
- **Parallel exploration.** Use up to 3 Explore agents for the codebase scan to maximize speed. Each agent covers a non-overlapping domain.
- **Graceful degradation.** If MCP tools aren't available, fall back to artisan commands or file exploration. If directories don't exist, skip silently.
- **CLAUDE.md awareness.** If the project has a `CLAUDE.md`, read it early — it often contains terminology rules, conventions, and architectural context that inform what counts as "stale" or "inconsistent."
