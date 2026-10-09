---
name: keyblade-statusbar-config
description: "Configure keyblade statusbar settings — theme, colors, HP/MP source, level, drive, world, display options."
user_invocable: true
---

# Keyblade Statusbar Configuration

When the user invokes /keyblade-statusbar-config, read the current config from `~/.claude/hooks/keyblade/config.json` and present all available settings so the user can pick what to change.

## Steps

1. Read the current config file at `~/.claude/hooks/keyblade/config.json`
2. Present an INTERACTIVE category selection using AskUserQuestion
3. After category is selected, show that category's current values and options using AskUserQuestion
4. Apply the change by editing the JSON file
5. Confirm the change with KH flavor

## Menu Format

Present settings as INTERACTIVE selections using the AskUserQuestion tool.

### Step 1: Category Selection

Use AskUserQuestion with:
- header: "Config"
- question: "KEYBLADE CONFIG — What do you want to change?"
- options: One per category, with current values previewed in the description
  - label: "Theme" / description: "Currently: full_rpg (classic, minimal, full_rpg)"
  - label: "HP" / description: "Currently: auto, budget $5.00, cure timer on"
  - label: "Keyblade Names" / description: "Opus → Ultima Weapon, Sonnet → Oathkeeper, Haiku → Kingdom Key, Fable → Sweet Memories"
  - label: "Level & EXP" / description: "per: 100, curve: linear, max: 99, source: lines"

Use UP TO 4 options per question. If there are more than 4 categories, use two questions. Good groupings:
- Question 1: Theme, HP & Auth, Level & EXP, Drive
- Question 2: World & PR, Keyblade Names, Colors, Display (munny/timer/focus/session/party panel)

After changing a setting, suggest `python3 ~/.claude/hooks/keyblade/keyblade.py --preview` to see every theme in the terminal.

### Step 2: Setting Selection

After a category is picked, show the specific settings within it using AskUserQuestion:
- header: The category name (e.g. "Theme")
- question: Show current value, ask what to change
- options: The available values or settings

Examples:

**Theme selected:**
- header: "Theme"
- question: "Current theme: full_rpg — Select new theme"
- options: classic, minimal, full_rpg

**Level selected:**
- header: "Level"
- question: "level_per: 100, curve: linear, max: 99, source: lines — What to change?"
- options: "level_per", "level_curve", "level_source", "level_max"

Then for the specific setting, show its options.

### Step 3: Apply & Confirm

After selection, apply the change and confirm with KH flavor.

## Available Settings Reference

### theme
Which statusline layout to use.
- `classic` — 2 lines: HP/MP bars + keyblade name, auth badge, world, PR, munny
- `minimal` — 1 line: keyblade name, auth badge, world, HP%, MP%, munny
- `full_rpg` — 3 lines: HP/MP bars, keyblade, auth, level, world, PR, drive gauge, EXP, munny, focus, timer, party member, session name

### hp_source
What the HP bar tracks. Goes down as usage increases.
- `auto` (default) — picks by how the session authenticates: claude.ai subscribers get whichever plan window (5-hour or 7-day) is closer to its cap; Claude apps gateway users get their spend limit; API key / Bedrock / Vertex / Foundry sessions, and Team/Enterprise plans (no plan limits in the payload), get cost_budget.
- `5_hour` — 5-hour plan usage window (Pro/Max). From the `rate_limits` field Claude Code sends.
- `7_day` — 7-day plan usage window (Pro/Max).
- `spend_limit` — Claude apps gateway spend limit (shows `$used/$limit`).
- `cost_budget` — session cost vs hp_budget_usd (API key users).

### hp_budget_usd
The per-session dollar budget for HP when using cost_budget (or auto on an API key). Default: 5.00. When a session spends this much, HP hits 0; it resets with each new session or /clear.

### show_hp_reset
Show the ✚ Cure countdown until the plan window resets. true/false. Default: true.

### show_auth
Show the ◈ auth badge: Max / Pro / Team / Enterprise (claude.ai plan), API (API key), OAuth, Bedrock / Vertex / Foundry / Gateway. true/false. Default: true.

### auth_cache_ttl
Seconds before re-checking `claude auth status` (runs in the background). Default: 600.

### keyblade_names
Map each Claude model to a keyblade name. The user can set any string they want.
- `opus` — default: "Ultima Weapon"
- `sonnet` — default: "Oathkeeper"
- `haiku` — default: "Kingdom Key"
- `fable` — default: "Sweet Memories"

Any key that appears in the model ID works, so the user can add new model families (e.g. `"mythos": "Kingdom Key D"`).

Some fun alternatives to suggest if asked:
- Opus: Oblivion, Fenrir, Decisive Pumpkin, Two Become One
- Sonnet: Star Seeker, Sleeping Lion, Bond of Flame, Winner's Proof
- Haiku: Dream Sword, Starlight, Fairy Harp, Wishing Star

### level_per
How many units per level-up. Default: 100. Lower = faster leveling.

### level_curve
How the level scales.
- `linear` — every `level_per` units = +1 level (steady progression)
- `exponential` — each level requires more than the last (RPG-authentic, early levels come fast)

### level_max
Maximum level cap. Default: 99 (like Kingdom Hearts).

### level_source
What counts toward leveling and EXP (EXP is tied to the same source).
- `lines` — total lines modified (added + removed)
- `added_only` — only lines added
- `commits` — your commits (by git user.email) since the session started; switching to a branch with older commits doesn't count
- `files` — files you've committed or changed since the session started; files already dirty at session start don't count

### show_drive
Show the drive gauge bar. true/false. Default: true. Only visible in full_rpg theme.

### drive_source
What fills the drive bar.
- `lines` — uncommitted line changes
- `files` — uncommitted file count
- `both` — files + lines combined

### drive_max_lines
Scale for 100% on the drive bar. Default: 1000. When uncommitted changes reach this number, the bar is full.

### drive_bar_width
Character width of the drive bar. Default: 10.

### drive_include_untracked
Whether to count untracked (new, not yet git-added) files in the drive total. Default: true.

### git_cache_ttl
Seconds to reuse git status between renders. Default: 5. Use 0 for always-fresh (slower in big repos).

### show_drive_form / drive_form_names / drive_form_colors
Drive Form shown for the reasoning effort level (`low`, `medium`, `high`, `xhigh`, `max`). Defaults: Valor (red), Wisdom (blue), Limit (bright_cyan), Master (bright_yellow), Final (bright_white). Hidden automatically when the model has no effort setting.

### show_world
Show the world (directory) name. Clicking it opens the repo in terminals that support links. true/false.

### show_branch
Show the git branch name after the directory (e.g. `myapp ∙ main ↑2`), with commits ahead/behind upstream. true/false. Default: true.

### show_pr
Show the open PR / MR badge (`#12 ✓`). ✓ approved, ✗ changes requested, ○ pending, ◌ draft. true/false. Default: true.

### show_worktree
Show `⎇ name` when the session is in a git worktree. true/false. Default: true.

### world_fallback
The world name shown when no directory is detected. Default: "Traverse Town".

### world_map
Map directory names to custom KH world names. Default: {} (empty, uses real directory names).
Example:
```json
{
  "world_map": {
    "myapp": "Hollow Bastion",
    "api-server": "The World That Never Was",
    "frontend": "Destiny Islands"
  }
}
```

### show_munny
Show the munny (cost) counter. true/false.

### show_timer
Show the journey timer (full_rpg theme only). true/false.

### show_focus
Show the ◎ Focus gauge — prompt cache hit ratio and time until a warm cache goes cold (full_rpg only). true/false. Default: true.

### show_session_name
Show the ✎ session name (from /rename or the AI-generated title). true/false. Default: true.

### show_fast_mode
Show ⚡ next to the keyblade when fast mode is on. true/false. Default: true.

### show_party
Show the `--agent` name as a party member. true/false. Default: true.

### show_vim_mode
Show `-- NORMAL --` etc. in the statusline. Default: false. If enabled, also suggest setting `"hideVimModeIndicator": true` in the `statusLine` block of `~/.claude/settings.json` so the mode isn't shown twice.

### party_panel
Render subagents as party members in Claude Code's agent panel (`subagentStatusLine`): `✦ Aladdin  "Searching…"  1m35s`, ✓ when done, ✗ KO when failed, ♥ only when their context runs low. true/false. Default: true.

### party_members
Choose which party member a subagent becomes, keyed by agent type or name: `{"Explore": "Tarzan", "my-agent": "Ariel"}`. Default: {} (built-in roles: security→Donald, test→Goofy, review→Riku, explore→Aladdin, plan→Mulan, debug→Tron, docs→Beast, PR/release→Jack Sparrow; others get world guests like Simba, Auron, Ariel). Only suggest real KH party members (characters who fight in Sora's party).

### responsive / hyperlinks / color_mode
- `responsive` — fit lines to the terminal width, dropping the least important segments first. Default: true.
- `hyperlinks` — clickable world/PR links (OSC 8). Default: true. Turn off if the terminal shows garbage.
- `color_mode` — `auto`, `truecolor`, `basic`, or `none`. Default: auto.

### colors
ANSI color names for each element. Available colors:
- `green`, `blue`, `cyan`, `yellow`, `red`, `magenta`, `white`
- Bright variants: `bright_green`, `bright_blue`, `bright_cyan`, `bright_yellow`, `bright_white`, `bright_orange`

Color assignments:
- `hp` — HP bar color when healthy (default: green). Auto-shifts to amber/red at low percentages.
- `mp` — MP bar color (default: blue)
- `munny` — Munny counter color (default: yellow)
- `keyblade` — Keyblade name color (default: cyan)
- `drive` — Drive gauge color when no Drive Form is shown (default: magenta)

## Rules

1. Always read the CURRENT config before showing settings (don't assume defaults)
2. After making a change, write the updated JSON back to the file with proper formatting (indent=2)
3. Only change what the user asks to change — preserve everything else
4. If the user asks to change multiple things at once, apply all changes in one write
5. Confirm each change with a brief KH-flavored message like "Equipped Oblivion!" or "World map updated!"
6. If the config file doesn't exist, create it with defaults first
