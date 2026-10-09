# Changelog

## 1.2.1

Fixed
- `keyblade.py --preview` left a `keyblade_preview_*` directory in `$TMPDIR` on every run; its scratch state is now removed when the preview finishes.

## 1.2.0

Changed
- **Party panel redesign** — subagents now join as real KH party members picked by role (security→Donald, tests→Goofy, review→Riku, explore→Aladdin, plan→Mulan, debug→Tron, docs→Beast, PR/release→Jack Sparrow; world guests like Simba and Auron for the rest) and "chatter" what they're doing: `✦ Aladdin  "Searching…"  1m35s`. ✦ twinkles while working, ✓ done with the total time, ✗ KO on failure. The per-row keyblade, Drive Form and MP bar are gone; ♥ shows only when a member's context runs low. Each subagent keeps its member for its whole run, and visible members never repeat.
- New `party_members` config to choose members by agent type or name.

## 1.1.1

Fixed
- A failed write (disk full, killed mid-write) could leave `settings.json` truncated; it's now replaced atomically, keeping symlinks, permissions and non-ASCII text.
- A wrong-typed value in `config.json` (e.g. `"colors": null`) blanked the statusline; bad values now fall back to defaults and any render error shows the fallback.
- Homebrew: `keyblade-setup` linked to the versioned keg, so `brew upgrade` left the statusline pointing at deleted files, and re-running setup then reset `config.json`. It now uses `opt_libexec` and only creates the config when it's missing. `install.sh` likewise keys updates off `config.json` and no longer writes through Homebrew's symlinks.
- `level_source: "commits"` / `"files"` counted another branch's history after a checkout, other people's pulled commits, files already dirty when the session started, and reset when the session changed directory. They now count your commits since the session started (plus files changed this session).
- 「LEVEL UP!」 flickered when two sessions worked in the same repo; level-up state is per session.
- HP was stuck at 100% for Team/Enterprise plans (no plan limits in the payload); `auto` now falls back to the cost budget.
- MP showed full when `remaining_percentage` was `0`.
- A file named `head` in the working directory (case-insensitive filesystems) broke the uncommitted line count.
- An untracked symlink to a FIFO could hang every render; only regular files are line-counted.
- Commands that merely contain "keyblade" (e.g. a wrapper script) were treated as keyblade's own and replaced without backup.
- Non-UTF-8 locales and lone surrogates in payload strings blanked the statusline.
- Long subagent names overflowed party panel rows.

Install
- `install.sh` and `keyblade-setup --theme=` reject unknown themes before changing anything.
- Uninstall also removes cached state from `$TMPDIR`.
- The per-project state map is pruned to the 50 most recent projects.

## 1.1.0

New
- **Auth badge** — `◈ Max` / `Pro` / `API` / `Bedrock` / ... shows how the session bills. Read from `claude auth status` in the background and cached (no email or org stored), with an environment-based guess until it lands.
- **`hp_source: "auto"`** (new default) — subscribers get whichever plan window is closer to its cap, gateway users their spend limit, API-key sessions their cost budget. New `spend_limit` source.
- **✚ Cure countdown** until the HP window resets.
- **PR badge** (`#12 ✓`, `!12` for GitLab MRs), colored by review state and clickable.
- **Clickable world** linking to the repo/branch, `↑ahead ↓behind`, `⎇ worktree`, `+N` added dirs.
- **◎ Focus gauge** (prompt cache hit ratio and time until it goes cold), **✎ session name**, **⚡ fast mode**, opt-in vim mode, party member in classic.
- **Party panel** — subagents rendered as party members via `subagentStatusLine` (`keyblade.py --party`).
- **Responsive layout** — lines fit `COLUMNS`; bars shrink and low-priority segments drop on narrow terminals.
- **`keyblade.py --preview`** renders every theme and state in the terminal.
- Fable models wield Sweet Memories; any `keyblade_names` key found in the model ID now matches.

Fixed
- HP no longer reads the keychain or calls the undocumented usage API; it uses the `rate_limits` Claude Code sends. API-key sessions no longer show a subscription's usage.
- Drive Form now follows the live `effort.level`, and is hidden for models without an effort setting instead of showing the settings.json value.
- `level_source: "commits"` / `"files"` were stuck at level 1 (they read payload fields that don't exist); they now count commits/files since the session started.
- Bars looked full in 16-color terminals (the empty track used the fill color as background).
- `colors.hp` and `colors.drive` were documented but ignored.
- Concurrent sessions could corrupt the shared state file; writes are now atomic and per-project state is keyed by full path.
- Git status runs once per render (cached 5s, `git_cache_ttl`) with `--no-optional-locks`, so the statusline no longer contends for `index.lock` with Claude's git commands. Untracked line counting no longer spawns a `wc` per file.
- No Save Point badge outside git repositories.
- Payload text (session name, branch, agent names) is stripped of control characters before printing.

Install
- The installer also registers `subagentStatusLine` and sets `refreshInterval: 30`; existing tweaks on a keyblade `statusLine` are kept. Settings registration lives in `keyblade.py` (shared by install.sh, uninstall.sh and Homebrew). The Homebrew setup now installs `/keyblade-statusbar-config` too.
- Tests are hermetic: temporary state, a fake `claude`, throwaway git repos.

## 1.0.2

- Fixed HP flashing to 100% on session start and after `/clear` when the plan-usage token lookup or API call transiently failed — now falls back to the last-known cached value.
- Fixed MP not moving after `/compact` — MP is now read directly from the transcript file (using `message.usage` token counts and `isCompactSummary` markers) rather than the statusline payload, which lags one turn behind.

## 1.0.1

- Added `xhigh` drive form tier — "Limit Form" now sits at `high`, "Master Form" moved up to `xhigh`.
- Adjusted `high`-tier drive form color from bright yellow to bright cyan.
- Fixed effort-level resolution to handle the Claude Code v2.1+ dict shape (`{"level": "..."}`) alongside the legacy plain-string form.

## 1.0.0

Initial release.

- Keyblade Status Line with 3 configurable themes: classic, minimal, full_rpg
- /kh-menu Command Menu skill with contextual Attack, Magic, Items, Summon categories
- Configurable MP source, keyblade names, colors, and display options
- Homebrew formula for easy installation
- Installer with statusline backup/restore
