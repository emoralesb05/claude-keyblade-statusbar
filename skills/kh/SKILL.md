---
name: kh
description: "Kingdom Hearts Command Menu — presents contextual dev actions as Attack, Magic, Items, and Summon."
user_invocable: true
---

# Kingdom Hearts Command Menu

When the user invokes /kh, present a Kingdom Hearts battle menu. Analyze the current project context (git status, recent changes, project type, open issues) and populate each category with relevant, actionable options.

## Menu Format

Present the menu using this exact box-drawing format:

```
 +===============================+
 |        COMMAND MENU           |
 +===============================+
 |                               |
 |  > ATTACK                     |
 |    1. [action]                |
 |    2. [action]                |
 |                               |
 |    MAGIC                      |
 |    1. [transform]             |
 |    2. [transform]             |
 |                               |
 |    ITEMS                      |
 |    1. [info]                  |
 |    2. [info]                  |
 |                               |
 |    SUMMON                     |
 |    1. [orchestrate]           |
 |    2. [orchestrate]           |
 |                               |
 +===============================+
```

Then say: **Select a command (e.g. "Attack 1") or describe your own action.**

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

### MAGIC (transformative, requires skill)

Things that CHANGE code intelligently:
- Refactor a module
- Fix a specific bug
- Optimize performance
- Add type annotations
- Improve error handling
- Apply DRY principles

Look at recent git changes, TODO comments, or code smells to suggest specific magic actions.

### ITEMS (informational, read-only)

Things that SHOW you information:
- Git status / diff
- Recent git log
- Show open TODOs
- Test coverage
- Dependency audit
- Code statistics

### SUMMON (delegative, spawns complex workflows)

Things that ORCHESTRATE multiple steps:
- Spawn sub-agents for parallel work
- Create a PR with full description
- Full pre-commit check pipeline
- Generate a test suite for untested code
- Comprehensive code review

## Rules

1. AT MOST 4 options per category (like KH's menu slots)
2. Number each option for easy selection
3. Only suggest actions that are relevant — don't suggest "Deploy" if there's no deploy config
4. When the user picks an option (by number or description), execute it immediately
5. Report results in KH flavor:
   - Success: "Obtained [result]!" or "[Action] complete! Gained [X] EXP!"
   - Failure: "The attack missed!" or "Not enough MP!" followed by the actual error
6. If the user just says a number, match it to the most recently presented menu

## Context Analysis

Before presenting the menu, silently analyze:
- `git status` to understand current state
- Project type (check for package.json, Gemfile, pyproject.toml, Cargo.toml, go.mod, etc.)
- Recent git log (last 5 commits) for context
- Any failing tests or lint issues from recent output

Use this context to populate the menu with RELEVANT options only.
