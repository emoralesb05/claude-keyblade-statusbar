# Keyblade

Kingdom Hearts themed statusline and command menu for Claude Code.

## Features

**Keyblade Status Line** — HP/MP bars, keyblade name, munny counter, and more displayed in the Claude Code status bar.

**Command Menu** — `/kh` slash command that presents contextual dev actions organized as Attack, Magic, Items, and Summon in KH battle menu style.

## Install

```bash
brew install emoralesb05/tap/claude-keyblade-statusbar
keyblade-setup
```

Or install directly from source:

```bash
git clone https://github.com/emoralesb05/claude-keyblade-statusbar.git
cd claude-keyblade-statusbar
bash install.sh
```

## Themes

Three configurable themes via `config.json`:

### Classic (default)

2-line display with HP bar (context remaining), MP bar (cost budget), keyblade name, world, and munny.

### Minimal

Single-line display with keyblade name, world, HP percentage, and munny.

### Full RPG

3-line display with HP/MP bars, keyblade name, level, world, drive gauge, EXP, munny, journey timer, and party member.

## Configuration

Edit `~/.claude/hooks/keyblade/config.json`:

```json
{
  "theme": "classic",
  "mp_source": "cost_budget",
  "mp_budget_usd": 5.00,
  "keyblade_names": {
    "opus": "Ultima Weapon",
    "sonnet": "Oathkeeper",
    "haiku": "Kingdom Key"
  },
  "show_munny": true,
  "show_world": true,
  "show_timer": true,
  "colors": {
    "hp": "green",
    "mp": "blue",
    "munny": "yellow",
    "keyblade": "cyan"
  }
}
```

### Options

| Key | Default | Description |
|-----|---------|-------------|
| `theme` | `"classic"` | `classic`, `minimal`, or `full_rpg` |
| `mp_source` | `"cost_budget"` | `cost_budget`, `context_remaining`, or `api_efficiency` |
| `mp_budget_usd` | `5.00` | Budget for MP bar when using cost_budget source |
| `keyblade_names` | see above | Model-to-keyblade name mapping |
| `show_munny` | `true` | Show munny (cost) counter |
| `show_world` | `true` | Show world (directory) name |
| `show_timer` | `true` | Show journey timer (full_rpg only) |
| `colors` | see above | ANSI color names for each element |

### Keyblade Names

Models map to keyblade names:

| Model | Default Keyblade |
|-------|-----------------|
| Opus | Ultima Weapon |
| Sonnet | Oathkeeper |
| Haiku | Kingdom Key |

### MP Sources

| Source | Description |
|--------|-------------|
| `cost_budget` | MP = remaining % of `mp_budget_usd` |
| `context_remaining` | MP = context window remaining % |
| `api_efficiency` | MP = API time / total time ratio |

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
