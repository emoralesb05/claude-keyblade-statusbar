---
name: keyblade-statusbar-config
description: "Configure keyblade statusbar settings — theme, colors, MP source, keyblade names, display options."
user_invocable: true
---

# Keyblade Statusbar Configuration

When the user invokes /keyblade-statusbar-config, read the current config from `~/.claude/hooks/keyblade/config.json` and present all available settings so the user can pick what to change.

## Steps

1. Read the current config file at `~/.claude/hooks/keyblade/config.json`
2. Present the current settings in a clear format (shown below)
3. Ask what they want to change
4. Apply the change by editing the JSON file
5. Confirm the change

## Display Format

Show the current config like this:

```
 +===============================+
 |    KEYBLADE CONFIG            |
 +===============================+
 |                               |
 |  THEME: classic               |
 |    > classic                  |
 |      minimal                  |
 |      full_rpg                 |
 |                               |
 |  MP SOURCE: cost_budget       |
 |    > cost_budget              |
 |      context_remaining        |
 |      api_efficiency           |
 |                               |
 |  MP BUDGET: $5.00             |
 |                               |
 |  KEYBLADE NAMES:              |
 |    Opus   → Ultima Weapon     |
 |    Sonnet → Oathkeeper        |
 |    Haiku  → Kingdom Key       |
 |                               |
 |  DISPLAY:                     |
 |    show_munny: true           |
 |    show_world: true           |
 |    show_timer: true           |
 |                               |
 |  COLORS:                      |
 |    hp: green                  |
 |    mp: blue                   |
 |    munny: yellow              |
 |    keyblade: cyan             |
 |                               |
 +===============================+
```

Then ask: **What would you like to change?**

## Available Settings Reference

### theme
Which statusline layout to use.
- `classic` — 2 lines: HP/MP bars + keyblade name, world, munny
- `minimal` — 1 line: keyblade name, world, HP%, munny
- `full_rpg` — 3 lines: HP/MP bars, keyblade, level, world, drive gauge, EXP, munny, timer, party member

### mp_source
What the MP bar tracks.
- `cost_budget` — MP = remaining % of mp_budget_usd (drains as you spend money)
- `context_remaining` — MP = context window remaining % (same as HP)
- `api_efficiency` — MP = ratio of API time to total session time

### mp_budget_usd
The dollar budget for MP when using cost_budget source. Default: 5.00. When you spend this much, MP hits 0.

### keyblade_names
Map each Claude model to a keyblade name. The user can set any string they want.
- `opus` — default: "Ultima Weapon"
- `sonnet` — default: "Oathkeeper"
- `haiku` — default: "Kingdom Key"

Some fun alternatives to suggest if asked:
- Opus: Oblivion, Fenrir, Decisive Pumpkin, Two Become One
- Sonnet: Star Seeker, Sleeping Lion, Bond of Flame, Winner's Proof
- Haiku: Dream Sword, Starlight, Fairy Harp, Wishing Star

### show_munny
Show the munny (cost) counter. true/false.

### show_world
Show the world (directory) name. true/false.

### show_timer
Show the journey timer (full_rpg theme only). true/false.

### colors
ANSI color names for each element. Available colors:
- `green`, `blue`, `cyan`, `yellow`, `red`, `magenta`, `white`
- Bright variants: `bright_green`, `bright_blue`, `bright_cyan`, `bright_yellow`, `bright_white`

Color assignments:
- `hp` — HP bar color (default: green)
- `mp` — MP bar color (default: blue)
- `munny` — Munny counter color (default: yellow)
- `keyblade` — Keyblade name color (default: cyan)

## Rules

1. Always read the CURRENT config before showing settings (don't assume defaults)
2. After making a change, write the updated JSON back to the file with proper formatting (indent=2)
3. Only change what the user asks to change — preserve everything else
4. If the user asks to change multiple things at once, apply all changes in one write
5. Confirm each change with a brief KH-flavored message like "Equipped Oblivion!" or "World map updated!"
6. If the config file doesn't exist, create it with defaults first
