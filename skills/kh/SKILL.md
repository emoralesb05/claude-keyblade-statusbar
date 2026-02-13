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
  - description: Preview the top action, e.g. "Run tests, commit, push..."

### Question 2: After category is selected, show that category's options
- header: The category name (e.g. "Attack")
- question: "Select a command"
- options: The 2-4 specific actions for that category
  - label: Short action name (max 30 chars)
  - description: What it does

After the user selects an action, EXECUTE it immediately. Do not ask for confirmation.

### KH Flavor
- For Magic options, prefix labels with spell names: "Cure —", "Fire —", "Thunder —", "Reflect —"
- For Summon options, prefix with character names: "Donald —", "Goofy —", "Riku —", "Naminé —"

## Category Definitions

### ATTACK (action-oriented, direct execution)

Things that DO something to the codebase or project:
- Run tests (detect framework: brew tests, npm test, pytest, cargo test, etc.)
- Build the project
- Create a commit
- Push changes
- Run linters/formatters
- Deploy

Analyze the project to determine which actions make sense. For a Ruby/Homebrew project, suggest `brew tests`, `brew typecheck`, `brew style`. For Node, suggest `npm test`, `npm run build`, etc.

### MAGIC (transformative, requires skill — context-driven)

Things that CHANGE code intelligently. Magic options should be SPECIFIC, not generic. Before populating this category, deeply analyze:

- **GitHub Issues**: Run `gh issue list --limit 5` to find open issues. Suggest fixing specific ones by title/number (e.g. "Fix #42: Login redirect loop").
- **PR Review Comments**: If on a PR branch, run `gh pr view --json reviewDecision,comments` to find unresolved review feedback. Suggest addressing specific comments.
- **CI Failures**: Run `gh run list --limit 3 --json status,conclusion,name` to check for failing CI checks. Suggest fixing the specific failure.
- **TODO/FIXME/HACK**: Grep for `TODO|FIXME|HACK|XXX` in recently modified files. Suggest resolving specific ones.
- **Code Smells**: Look at recent git diff for long functions, duplicated code, missing error handling. Suggest specific refactors.
- **Type Errors / Lint Warnings**: Check for linter/type-checker output if available.

Magic options should read like spells with targets. Pick the spell that best matches the action:

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

Things that SHOW you information:
- Git status / diff
- Recent git log
- Show open TODOs
- Test coverage
- Dependency audit
- Code statistics
- Open PRs awaiting review

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

Name summons after KH characters when spawning agents:
- Security review → "Summon Donald" (defensive magic)
- Test generation → "Summon Goofy" (reliable support)
- Code review → "Summon Riku" (rival's sharp eye)
- Documentation → "Summon Naminé" (the chronicler)
- PR creation → "Summon Kairi" (the heart that connects)
- Bug investigation → "Summon Roxas" (sees what others miss)
- Full pipeline orchestration → "Summon Mickey" (the King, runs everything)

## Rules

1. AT MOST 4 options per category (like KH's menu slots)
2. Number each option for easy selection
3. Only suggest actions that are relevant — don't suggest "Deploy" if there's no deploy config
4. Magic options MUST be specific to the current codebase state, never generic
5. When the user picks an option (by number or description), execute it immediately
6. Report results in KH flavor:
   - Success: "Obtained [result]!" or "[Action] complete! Gained [X] EXP!"
   - Failure: "The attack missed!" or "Not enough MP!" followed by the actual error
7. If the user just says a number, match it to the most recently presented menu

## Context Analysis

Before presenting the menu, silently analyze (run these in parallel where possible):
- `git status` and `git diff --stat` to understand current state
- `git log --oneline -5` for recent context
- Project type (check for package.json, Gemfile, pyproject.toml, Cargo.toml, go.mod, etc.)
- `gh issue list --limit 5 --json number,title,labels` for open issues
- `gh pr view --json number,title,reviewDecision,statusCheckRollup` if on a PR branch
- `gh run list --limit 3 --json status,conclusion,name` for CI status
- Grep for `TODO|FIXME|HACK` in recently changed files (`git diff --name-only HEAD~5` then grep those files)

Use this context to populate the menu with RELEVANT, SPECIFIC options only. The more specific each option is, the more useful the menu becomes.
