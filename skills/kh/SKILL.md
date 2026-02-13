---
name: kh
description: "Kingdom Hearts Command Menu — presents contextual dev actions as Attack, Magic, Items, and Summon."
user_invocable: true
---

# Kingdom Hearts Command Menu

When the user invokes /kh, present a Kingdom Hearts battle menu. Deeply analyze the current project context and populate each category with specific, actionable options tailored to the current state of the codebase.

## Menu Format

Present the menu as INTERACTIVE selections using the AskUserQuestion tool. Use TWO question blocks:

### Question 1: Category selection
- header: "Command"
- question: "COMMAND MENU — Select a category"
- options: One per category with the best/most relevant option previewed in the description
  - label: "Attack" / "Magic" / "Items" / "Summon"
  - description: Preview the top action, e.g. "Strike Raid: run tests, Sonic Blade: commit..."

### Question 2: After category is selected, show that category's options
- header: The category name (e.g. "Attack")
- question: "Select a command"
- options: The 2-4 specific actions for that category
  - label: Short action name (max 30 chars)
  - description: What it does

After the user selects an action, EXECUTE it immediately. Do not ask for confirmation.

### KH Flavor
- For Attack options, prefix labels with ability names: "Strike Raid —", "Sonic Blade —", etc.
- For Magic options, prefix labels with spell names: "Cure —", "Fire —", "Thunder —", etc.
- For Items options, prefix labels with item names: "Potion —", "Ether —", "Elixir —", etc.
- For Summon options, prefix with character names: "Donald —", "Goofy —", "Riku —", etc.

## Category Definitions

### ATTACK (action-oriented, direct execution)

Things that DO something to the codebase or project. Name each attack after a KH ability:

#### Ability Reference — match the ability to the action:
| Ability | Use for | Example |
|---------|---------|---------|
| **Strike Raid** | Run tests (throw and see what hits) | "Strike Raid — Run pytest" |
| **Sonic Blade** | Run linters/formatters (fast, clean cuts) | "Sonic Blade — Run eslint --fix" |
| **Ars Arcanum** | Build the project (combo of steps) | "Ars Arcanum — npm run build" |
| **Ragnarok** | Deploy (the big finisher) | "Ragnarok — Deploy to production" |
| **Sliding Dash** | Push changes (dash forward) | "Sliding Dash — Push to origin" |
| **Zantetsuken** | Create a commit (one clean cut) | "Zantetsuken — Commit all changes" |
| **Ripple Drive** | Run full CI pipeline locally | "Ripple Drive — lint + test + build" |
| **Stun Impact** | Kill processes, clean up | "Stun Impact — Kill stale dev servers" |

Analyze the project to determine which actions make sense. For a Python project, suggest `pytest`. For Node, suggest `npm test`, `npm run build`, etc. Also check for available skills/commands (like `/commit`) and suggest those where relevant.

### MAGIC (transformative, requires skill — context-driven)

Things that CHANGE code intelligently. Magic options should be SPECIFIC, not generic. Before populating this category, deeply analyze:

- **GitHub Issues**: Run `gh issue list --limit 5` to find open issues. Suggest fixing specific ones by title/number (e.g. "Fix #42: Login redirect loop").
- **PR Review Comments**: If on a PR branch, run `gh pr view --json reviewDecision,comments` to find unresolved review feedback. Suggest addressing specific comments.
- **CI Failures**: Run `gh run list --limit 3 --json status,conclusion,name` to check for failing CI checks. Suggest fixing the specific failure.
- **TODO/FIXME/HACK**: Grep for `TODO|FIXME|HACK|XXX` in recently modified files. Suggest resolving specific ones.
- **Code Smells**: Look at recent git diff for long functions, duplicated code, missing error handling. Suggest specific refactors.
- **Type Errors / Lint Warnings**: Check for linter/type-checker output if available.

#### Spell Reference — match the spell to the situation:
| Spell | Use for | Example |
|-------|---------|---------|
| **Fire** | Fix breaking bugs, delete dead code | "Fire — Fix CI: failing typecheck" |
| **Blizzard** | Pin/lock dependencies, freeze versions | "Blizzard — Pin lodash to 4.17.21" |
| **Thunder** | Quick lint/format fixes | "Thunder — Resolve 3 lint warnings in auth" |
| **Cure** | Fix bugs, heal broken code | "Cure — Fix #42: API timeout" |
| **Aero** | Performance optimization | "Aero — Optimize slow DB query in users" |
| **Gravity** | Reduce size, simplify, compress | "Gravity — Reduce bundle size (remove unused)" |
| **Stop** | Revert, undo, stash changes | "Stop — Revert broken migration" |
| **Magnet** | Consolidate duplicates, DRY | "Magnet — Deduplicate auth logic (3 files)" |
| **Reflect** | Address PR review feedback | "Reflect — Address review: add validation" |
| **Water** | Refactor control flow, restructure | "Water — Refactor nested callbacks to async" |
| **Holy** | Add type safety, annotations | "Holy — Add type hints to keyblade.py" |
| **Flare** | Major refactor, big change | "Flare — Extract API client into module" |
| **Meteor** | Breaking changes, migrations | "Meteor — Migrate config schema v1 to v2" |
| **Ultima** | Complete overhaul of a system | "Ultima — Rewrite test suite with fixtures" |

NOT generic options like "Refactor a module" or "Fix a bug". Always pick the right spell for the job.

### ITEMS (informational, read-only)

Things that SHOW you information. Name each item after a KH consumable:

#### Item Reference — match the item to the info:
| Item | Use for | Example |
|------|---------|---------|
| **Potion** | Quick status check (git status/diff) | "Potion — Git status & diff" |
| **Ether** | Show context/resource info (coverage, stats) | "Ether — Test coverage report" |
| **Elixir** | Full project health check | "Elixir — Code stats (LOC, funcs, tests)" |
| **Mega-Potion** | Show recent history (git log) | "Mega-Potion — Recent git log (10 commits)" |
| **Hi-Potion** | Show open issues/PRs | "Hi-Potion — Open PRs awaiting review" |
| **Megalixir** | Full dependency/security audit | "Megalixir — Dependency audit" |
| **Tent** | Show TODOs/FIXMEs across codebase | "Tent — Show open TODOs (all files)" |
| **Save Point** | Show current branch/stash state | "Save Point — Branches & stashes" |

### SUMMON (delegative, spawns complex workflows — party-aware)

Things that ORCHESTRATE multiple steps. Before populating, check for running subagents and active work:

- **Party Check**: Look at the current session for any running or recently completed subagents. If agents are active, show their status:
  - "Donald is running security review..."
  - "Goofy completed test generation (3m ago)"
- **Available Summons**: Suggest workflows that benefit from parallelism:
  - Spawn sub-agents for parallel work (code review + test gen + docs)
  - Create a PR with full description
  - Full pre-commit check pipeline (lint + test + typecheck in parallel)
  - Generate a test suite for untested code
  - Comprehensive code review across multiple files
  - Security audit with dedicated agent

#### Character Reference — match the character to the workflow:
| Character | Role | Example |
|-----------|------|---------|
| **Donald** | Security review (defensive magic) | "Donald — Security audit" |
| **Goofy** | Test generation (reliable support) | "Goofy — Generate test suite" |
| **Riku** | Code review (rival's sharp eye) | "Riku — Review all changes" |
| **Naminé** | Documentation (the chronicler) | "Naminé — Generate changelog" |
| **Kairi** | PR creation (the heart that connects) | "Kairi — Create PR with description" |
| **Roxas** | Bug investigation (sees what others miss) | "Roxas — Investigate flaky test" |
| **Mickey** | Full pipeline (the King, runs everything) | "Mickey — Lint + test + build + deploy" |

## Skill & Command Awareness

Before building the menu, check what skills and commands are available in the current session. Look for installed skills that could be surfaced as options:

- If a `/commit` skill exists → suggest it under Attack (as "Zantetsuken — /commit")
- If a `/review-pr` skill exists → suggest it under Summon
- If a `/find-skills` skill exists → mention it if no good options are found for a category
- Check the system-reminder at the top of messages for available skill names
- When a skill matches an action, prefer invoking the skill over raw commands

This makes the menu a hub that connects to the user's full toolkit.

## Rules

1. AT MOST 4 options per category (like KH's menu slots)
2. Number each option for easy selection
3. Only suggest actions that are relevant — don't suggest "Ragnarok — Deploy" if there's no deploy config
4. Magic options MUST be specific to the current codebase state, never generic
5. When the user picks an option (by number or description), execute it immediately
6. Report results in KH flavor:
   - Success: "Obtained [result]!" or "[Action] complete! Gained [X] EXP!"
   - Failure: "The attack missed!" or "Not enough MP!" followed by the actual error
7. If the user just says a number, match it to the most recently presented menu
8. Surface relevant installed skills/commands where they fit a category

## Context Analysis

Before presenting the menu, silently analyze (run these in parallel where possible):
- `git status` and `git diff --stat` to understand current state
- `git log --oneline -5` for recent context
- Project type (check for package.json, Gemfile, pyproject.toml, Cargo.toml, go.mod, etc.)
- `gh issue list --limit 5 --json number,title,labels` for open issues
- `gh pr view --json number,title,reviewDecision,statusCheckRollup` if on a PR branch
- `gh run list --limit 3 --json status,conclusion,name` for CI status
- Grep for `TODO|FIXME|HACK` in recently changed files (`git diff --name-only HEAD~5` then grep those files)
- Check available skills in the session (from system-reminder tags)

### npm Scripts Discovery

If a `package.json` exists in the project root, read its `scripts` section and use those to populate Attack and Magic:
- **Attack**: Map common scripts to attack abilities:
  - `test` / `test:*` → "Strike Raid — npm test"
  - `build` → "Sonic Blade — npm run build"
  - `lint` / `eslint` → "Sliding Dash — npm run lint"
  - `format` / `prettier` → "Zantetsuken — npm run format"
  - `start` / `dev` → "Ars Arcanum — npm run dev"
  - `typecheck` / `tsc` → "Ripple Drive — npm run typecheck"
  - `deploy` → "Ragnarok — npm run deploy"
- **Magic**: If there are less common or project-specific scripts (e.g. `migrate`, `seed`, `codegen`, `storybook`), surface them as spell options when relevant.

Always prefer the project's actual scripts over guessing generic commands.

Use this context to populate the menu with RELEVANT, SPECIFIC options only. The more specific each option is, the more useful the menu becomes.
