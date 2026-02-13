# Keyblade

Kingdom Hearts themed statusline and command menu for Claude Code.

## Features

**Keyblade Status Line** — HP/MP bars, keyblade name, munny counter, and more displayed in the Claude Code status bar.

**Command Menu** — `/kh` slash command that presents contextual dev actions organized as Attack, Magic, Items, and Summon in KH battle menu style.

## Install

One-liner (curl):

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/emoralesb05/claude-keyblade-statusbar/main/install.sh)
```

Or clone and install:

```bash
git clone https://github.com/emoralesb05/claude-keyblade-statusbar.git
cd claude-keyblade-statusbar
bash install.sh
```

Or via Homebrew:

```bash
brew install emoralesb05/tap/claude-keyblade-statusbar
keyblade-setup
```

## Themes

Three configurable themes via `config.json`:

### Classic (default)

2-line display with HP bar (plan usage), MP bar (context remaining), keyblade name, world, and munny.

### Minimal

Single-line display with keyblade name, world, HP percentage, and munny.

### Full RPG

3-line display with HP/MP bars, keyblade name, level, world:branch (#PR), drive gauge (uncommitted changes), EXP, munny, journey timer, and party member.

## Configuration

Edit `~/.claude/hooks/keyblade/config.json`:

```json
{
  "theme": "classic",
  "hp_source": "5_hour",
  "hp_budget_usd": 5.00,
  "hp_usage_cache_ttl": 60,
  "show_drive": true,
  "drive_max_lines": 500,
  "drive_source": "lines",
  "drive_bar_width": 10,
  "drive_include_untracked": true,
  "level_per": 100,
  "level_curve": "linear",
  "level_max": 99,
  "level_source": "lines",
  "keyblade_names": {
    "opus": "Ultima Weapon",
    "sonnet": "Oathkeeper",
    "haiku": "Kingdom Key"
  },
  "show_munny": true,
  "show_world": true,
  "show_branch": true,
  "show_timer": true,
  "world_fallback": "Traverse Town",
  "world_map": {},
  "colors": {
    "hp": "green",
    "mp": "blue",
    "munny": "yellow",
    "keyblade": "cyan",
    "drive": "magenta"
  }
}
```

### HP (Plan Usage)

| Key | Default | Description |
|-----|---------|-------------|
| `hp_source` | `"5_hour"` | `5_hour`, `7_day` (Max/Pro), or `cost_budget` (API key users) |
| `hp_budget_usd` | `5.00` | Budget when using `cost_budget` source |
| `hp_usage_cache_ttl` | `60` | Seconds between plan usage API calls |

### Level & EXP

| Key | Default | Description |
|-----|---------|-------------|
| `level_per` | `100` | Units per level-up |
| `level_curve` | `"linear"` | `linear` or `exponential` (RPG-style scaling) |
| `level_max` | `99` | Level cap |
| `level_source` | `"lines"` | `lines` (added+removed), `added_only`, `commits`, or `files` |

EXP is tied to the same source as level.

### Drive (Uncommitted Changes)

| Key | Default | Description |
|-----|---------|-------------|
| `show_drive` | `true` | Toggle drive gauge (full_rpg only) |
| `drive_source` | `"lines"` | `lines`, `files`, or `both` |
| `drive_max_lines` | `500` | Scale for 100% on the bar |
| `drive_bar_width` | `10` | Character width of the bar |
| `drive_include_untracked` | `true` | Count untracked files |
| `colors.drive` | `"magenta"` | Drive bar color |

### World

| Key | Default | Description |
|-----|---------|-------------|
| `show_world` | `true` | Show world name |
| `show_branch` | `true` | Append `:branch` to world name |
| `world_fallback` | `"Traverse Town"` | Name when no directory detected |
| `world_map` | `{}` | Map directory names to custom KH world names |

### Display & Colors

| Key | Default | Description |
|-----|---------|-------------|
| `theme` | `"classic"` | `classic`, `minimal`, or `full_rpg` |
| `show_munny` | `true` | Show munny (cost) counter |
| `show_timer` | `true` | Show journey timer (full_rpg only) |
| `colors.hp` | `"green"` | HP bar (auto-shifts yellow/red at low %) |
| `colors.mp` | `"blue"` | MP bar |
| `colors.munny` | `"yellow"` | Munny counter |
| `colors.keyblade` | `"cyan"` | Keyblade name |

### Keyblade Names

| Model | Default |
|-------|---------|
| Opus | Ultima Weapon |
| Sonnet | Oathkeeper |
| Haiku | Kingdom Key |

## Command Menu

Use `/kh` in Claude Code to open the command menu. Claude analyzes your project and presents relevant actions in four KH-themed categories:

- **Attack** — Direct actions (run tests, build, commit, lint)
- **Magic** — Code transformations (refactor, fix bugs, optimize)
- **Items** — Information (git status, logs, TODOs, coverage)
- **Summon** — Complex workflows (create PR, code review, spawn agents)

## Uninstall

```bash
keyblade-setup --uninstall
```

Or if installed from source:

```bash
bash ~/.claude/hooks/keyblade/uninstall.sh
```

## License

MIT
