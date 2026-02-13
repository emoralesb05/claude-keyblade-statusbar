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
  - label: "HP" / description: "Currently: 5_hour, budget $5.00, cache 60s"
  - label: "Keyblade Names" / description: "Opus → Ultima Weapon, Sonnet → Oathkeeper, Haiku → Kingdom Key"
  - label: "Level & EXP" / description: "per: 100, curve: linear, max: 99, source: lines"

Use UP TO 4 options per question. If there are more than 4 categories, use two questions. Good groupings:
- Question 1: Theme, HP, Level & EXP, Drive
- Question 2: World, Keyblade Names, Colors, Display (munny/timer)

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
- `classic` — 2 lines: HP/MP bars + keyblade name, world, munny
- `minimal` — 1 line: keyblade name, world, HP%, munny
- `full_rpg` — 3 lines: HP/MP bars, keyblade, level, world, drive gauge, EXP, munny, timer, party member

### hp_source
What the HP bar tracks. Goes down as usage increases.
- `5_hour` — 5-hour plan usage window (Max/Pro users). Pulls from Anthropic usage API.
- `7_day` — 7-day plan usage window (Max/Pro users). Pulls from Anthropic usage API.
- `cost_budget` — session cost vs hp_budget_usd (API key users without Max/Pro)

### hp_budget_usd
The dollar budget for HP when using cost_budget source. Default: 5.00. When you spend this much, HP hits 0.

### hp_usage_cache_ttl
How often (in seconds) to re-fetch plan usage from the API. Default: 60. Lower = more up-to-date but more API calls.

### keyblade_names
Map each Claude model to a keyblade name. The user can set any string they want.
- `opus` — default: "Ultima Weapon"
- `sonnet` — default: "Oathkeeper"
- `haiku` — default: "Kingdom Key"

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
- `commits` — number of commits
- `files` — number of files changed

### show_drive
Show the drive gauge bar. true/false. Default: true. Only visible in full_rpg theme.

### drive_source
What fills the drive bar.
- `lines` — uncommitted line changes
- `files` — uncommitted file count
- `both` — files + lines combined

### drive_max_lines
Scale for 100% on the drive bar. Default: 500. When uncommitted changes reach this number, the bar is full.

### drive_bar_width
Character width of the drive bar. Default: 10.

### drive_include_untracked
Whether to count untracked (new, not yet git-added) files in the drive total. Default: true.

### show_world
Show the world (directory) name. true/false.

### show_branch
Show the git branch name after the directory (e.g. `myapp:main`). true/false. Default: true.

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

### colors
ANSI color names for each element. Available colors:
- `green`, `blue`, `cyan`, `yellow`, `red`, `magenta`, `white`
- Bright variants: `bright_green`, `bright_blue`, `bright_cyan`, `bright_yellow`, `bright_white`

Color assignments:
- `hp` — HP bar color (default: green). Note: HP bar auto-shifts to yellow/red at low percentages.
- `mp` — MP bar color (default: blue)
- `munny` — Munny counter color (default: yellow)
- `keyblade` — Keyblade name color (default: cyan)
- `drive` — Drive gauge color (default: magenta)

## Rules

1. Always read the CURRENT config before showing settings (don't assume defaults)
2. After making a change, write the updated JSON back to the file with proper formatting (indent=2)
3. Only change what the user asks to change — preserve everything else
4. If the user asks to change multiple things at once, apply all changes in one write
5. Confirm each change with a brief KH-flavored message like "Equipped Oblivion!" or "World map updated!"
6. If the config file doesn't exist, create it with defaults first
