# Keyblade

Kingdom Hearts themed statusline and command menu for Claude Code.

## Features

**Keyblade Status Line** — HP/MP bars, keyblade name, auth badge, munny counter, and more displayed in the Claude Code status bar.

**Party Panel** — subagents show up as party members (keyblade, Drive Form, MP bar) in Claude Code's agent panel.

**Command Menu** — `/kh-menu` slash command that presents contextual dev actions organized as Attack, Magic, Items, and Summon in KH battle menu style.

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

The installer registers `statusLine` (with `refreshInterval: 30` so countdowns tick while idle) and `subagentStatusLine` in `settings.json`. Any non-keyblade entries are backed up and restored on uninstall.

Preview every theme and state in your terminal:

```bash
python3 ~/.claude/hooks/keyblade/keyblade.py --preview            # all themes
python3 ~/.claude/hooks/keyblade/keyblade.py --preview full_rpg --width 80
```

## Themes

Three configurable themes via `config.json`:

### Classic (default)

```
  ✧ ███████████▌     72%  🗝  Ultima Weapon  ◈ Max  ✦ myapp ∙ main  #12 ○
  ♥ ██████████████▉          62% ✚ 2h13m  ✶ Master Form  ◉ 184  ✎ statusbar refresh
```

2 lines: MP bar (context), keyblade, auth badge, world ∙ branch, PR / HP bar (plan usage), Cure countdown, Drive Form, munny.

### Minimal

```
  🗝  Ultima Weapon  ◈ Max  ✶ Master  ✦ myapp ∙ main  #12 ○  ♥ 62% ✚ 2h13m  ✧ 72%  ◉ 184
```

### Full RPG

```
  ✧ ███████████▌     72%  🗝  Ultima Weapon  ◈ Max  ✦ myapp ∙ main  #12 ○
  ♥ ██████████████▉          62% ✚ 2h13m  LV 6 (♛ 500)
  ◆ ███▌       35%  ✶ Master Form  ◉ 184  ◎ 91% 41m  ⏱ 41m00s  ✎ statusbar refresh
```

3 lines: adds level/EXP, the Drive gauge (uncommitted changes), Focus gauge (prompt cache), journey timer, party member, and session name.

All themes fit the terminal width (Claude Code passes `COLUMNS`): on narrow terminals bars shrink and the least important segments drop first.

## What's on the HUD

| Element | Meaning |
|---|---|
| ♥ HP | Plan usage left (subscribers), gateway spend limit, or session cost vs budget (API key) — see `hp_source` |
| ✚ Cure | Countdown until the HP window resets |
| ✧ MP | Context window remaining. `「MP CHARGE」` below 10% |
| 🗝 Keyblade | Model: Opus → Ultima Weapon, Sonnet → Oathkeeper, Haiku → Kingdom Key, Fable → Sweet Memories. ⚡ = fast mode |
| ◈ Auth | How the session bills: `Max` / `Pro` / `Team` / `Enterprise` (claude.ai plan), `API` (API key or apiKeyHelper), `OAuth` (token), `Bedrock` / `Vertex` / `Foundry` / `Gateway` |
| ✶ Drive Form | Reasoning effort: Valor (low) → Wisdom (medium) → Limit (high) → Master (xhigh) → Final (max). Hidden when the model has no effort setting. Anti Form when context or HP runs out |
| ✦ World | Directory (click to open the repo), `∙ branch`, `↑ahead ↓behind`, `⎇ worktree`, `+N` added dirs |
| #12 ○ | Open PR (`!12` for GitLab MRs): ✓ approved, ✗ changes requested, ○ pending, ◌ draft. Click to open |
| ◆ Drive | Uncommitted changes (full_rpg) |
| ◎ Focus | Prompt cache hit ratio and time until a warm cache goes cold (full_rpg) |
| ◉ Munny | Session cost in cents |
| LV / ♛ EXP | Level and EXP from lines changed, commits, or files touched this session (full_rpg) |
| ✎ Journal | Session name from `/rename` or the AI title |
| ♦ Party | `--agent` name |
| 「SAVE POINT」 「LEVEL UP!」 「DANGER」 | Working tree just became clean · level increased · HP critical |

### How the auth badge works

Claude Code doesn't put the auth method in the statusline payload, so keyblade asks `claude auth status --json` in a background process and caches the answer (no email or org is stored) for `auth_cache_ttl` seconds. Until it lands, it guesses from the environment (`ANTHROPIC_API_KEY`, `CLAUDE_CODE_USE_BEDROCK`, `apiKeyHelper`, ...). Plan rate limits in the payload always mean a claude.ai subscription.

## Party Panel

The installer sets `subagentStatusLine` to `keyblade.py --party`. Each subagent row becomes:

```
▸ ♦ Explore  🗝  Kingdom Key  ✶ Valor  ✧ ████▉  81%  ⏱ 1m35s  Searching for statusline payload handling
✓ ♦ code-reviewer  🗝  Ultima Weapon  ✶ Master  ✧ ██     36%  Reviewed keyblade.py: 2 findings
```

Set `"party_panel": false` to keep Claude Code's default rows.

## Configuration

Edit `~/.claude/hooks/keyblade/config.json` (or run `/keyblade-statusbar-config`). The shipped `config.json` lists every key with its default.

### HP

| Key | Default | Description |
|-----|---------|-------------|
| `hp_source` | `"auto"` | `auto`, `5_hour`, `7_day`, `spend_limit`, or `cost_budget` |
| `hp_budget_usd` | `5.00` | Budget for `cost_budget` (and `auto` on API keys) |
| `show_hp_reset` | `true` | Show the ✚ Cure countdown |

`auto` picks by auth: claude.ai subscribers get whichever plan window (5-hour or 7-day) is closer to its cap; Claude apps gateway users get their spend limit; API key, Bedrock, Vertex and Foundry sessions get session cost vs `hp_budget_usd`.

Plan usage comes from the `rate_limits` field Claude Code sends (no keychain or network access). Before a session's first response, the last known values are reused so HP doesn't flash to 100%.

### Auth

| Key | Default | Description |
|-----|---------|-------------|
| `show_auth` | `true` | Show the ◈ auth badge |
| `auth_cache_ttl` | `600` | Seconds before re-checking `claude auth status` |

### Level & EXP

| Key | Default | Description |
|-----|---------|-------------|
| `level_per` | `100` | Units per level-up |
| `level_curve` | `"linear"` | `linear` or `exponential` (RPG-style scaling) |
| `level_max` | `99` | Level cap |
| `level_source` | `"lines"` | `lines` (added+removed), `added_only`, `commits` (made this session), or `files` (touched this session) |

EXP is tied to the same source as level.

### Drive (Uncommitted Changes)

| Key | Default | Description |
|-----|---------|-------------|
| `show_drive` | `true` | Toggle drive gauge (full_rpg only) |
| `drive_source` | `"lines"` | `lines`, `files`, or `both` |
| `drive_max_lines` | `1000` | Scale for 100% on the bar |
| `drive_bar_width` | `10` | Character width of the bar |
| `drive_include_untracked` | `true` | Count untracked files |
| `git_cache_ttl` | `5` | Seconds to reuse git status between renders (`0` = always fresh) |
| `show_drive_form` | `true` | Show the Drive Form name |
| `drive_form_names` | Valor … Final | Form name per effort level (`low`, `medium`, `high`, `xhigh`, `max`) |
| `drive_form_colors` | red … bright_white | Form color per effort level |

### World

| Key | Default | Description |
|-----|---------|-------------|
| `show_world` | `true` | Show world name |
| `show_branch` | `true` | Append `∙ branch` (with ↑↓ ahead/behind) |
| `show_pr` | `true` | Show the open PR / MR badge |
| `show_worktree` | `true` | Show `⎇ name` inside a git worktree |
| `world_fallback` | `"Traverse Town"` | Name when no directory detected |
| `world_map` | `{}` | Map directory names to custom KH world names |

### Display & Colors

| Key | Default | Description |
|-----|---------|-------------|
| `theme` | `"classic"` | `classic`, `minimal`, or `full_rpg` |
| `color_mode` | `"auto"` | `auto`, `truecolor`, `basic`, or `none` |
| `responsive` | `true` | Fit lines to the terminal width |
| `hyperlinks` | `true` | Clickable world/PR links (OSC 8; iTerm2, Kitty, WezTerm, ...) |
| `show_munny` | `true` | Show munny (cost) counter |
| `show_timer` | `true` | Show journey timer (full_rpg only) |
| `show_focus` | `true` | Show the ◎ Focus (prompt cache) gauge (full_rpg only) |
| `show_session_name` | `true` | Show the ✎ session name |
| `show_fast_mode` | `true` | Show ⚡ when fast mode is on |
| `show_party` | `true` | Show the `--agent` party member |
| `show_vim_mode` | `false` | Show `-- NORMAL --` etc. Pair with `"hideVimModeIndicator": true` in the `statusLine` settings |
| `party_panel` | `true` | Render subagent rows (`--party` mode) |
| `colors.hp` | `"green"` | HP bar when healthy (shifts amber/red when low) |
| `colors.mp` | `"blue"` | MP bar |
| `colors.munny` | `"yellow"` | Munny counter |
| `colors.keyblade` | `"cyan"` | Keyblade name |
| `colors.drive` | `"magenta"` | Drive bar when no Drive Form is shown |

### Keyblade Names

| Model | Default |
|-------|---------|
| Opus | Ultima Weapon |
| Sonnet | Oathkeeper |
| Haiku | Kingdom Key |
| Fable | Sweet Memories |

Any key in `keyblade_names` that appears in the model ID works, so new model families can be named without a code change. Unknown models wield Starlight.

## Command Menu

Use `/kh-menu` in Claude Code to open the command menu. Claude analyzes your project and presents relevant actions in four KH-themed categories:

- **Attack** — Direct actions (run tests, build, commit, lint)
- **Magic** — Code transformations (refactor, fix bugs, optimize)
- **Items** — Information (git status, logs, TODOs, coverage)
- **Summon** — Complex workflows (create PR, code review, spawn agents)

## Development

```bash
python3 -m unittest test_keyblade      # hermetic: temp state, fake `claude`, throwaway git repos
python3 keyblade.py --preview          # eyeball every theme and state
```

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
