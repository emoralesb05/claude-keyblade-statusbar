#!/usr/bin/env python3
"""keyblade.py — Kingdom Hearts themed statusline for Claude Code."""

import json
import math
import os
import subprocess
import sys
import tempfile
import time
import urllib.request

# ─── Configuration ───────────────────────────────────────────────

DEFAULT_CONFIG = {
    "theme": "classic",
    "color_mode": "auto",
    "hp_source": "5_hour",
    "hp_budget_usd": 5.00,
    "hp_usage_cache_ttl": 60,
    "show_drive": True,
    "drive_max_lines": 500,
    "drive_source": "lines",
    "drive_bar_width": 10,
    "drive_include_untracked": True,
    "level_per": 100,
    "level_curve": "linear",
    "level_max": 99,
    "level_source": "lines",
    "keyblade_names": {
        "opus": "Ultima Weapon",
        "sonnet": "Oathkeeper",
        "haiku": "Kingdom Key",
    },
    "show_munny": True,
    "show_world": True,
    "show_branch": True,
    "show_timer": True,
    "show_drive_form": True,
    "drive_form_names": {
        "low": "Valor Form",
        "medium": "Wisdom Form",
        "high": "Master Form",
        "max": "Final Form",
    },
    "drive_form_colors": {
        "low": "red",
        "medium": "blue",
        "high": "bright_yellow",
        "max": "bright_white",
    },
    "world_fallback": "Traverse Town",
    "world_map": {},
    "colors": {
        "hp": "green",
        "mp": "blue",
        "munny": "yellow",
        "keyblade": "cyan",
        "drive": "magenta",
    },
}

# ─── ANSI Color Helpers ─────────────────────────────────────────

# Basic 16-color ANSI (maximum compatibility)
ANSI_BASIC = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "green": "\033[32m",
    "blue": "\033[34m",
    "cyan": "\033[36m",
    "yellow": "\033[33m",
    "red": "\033[31m",
    "magenta": "\033[35m",
    "white": "\033[37m",
    "bright_green": "\033[92m",
    "bright_blue": "\033[94m",
    "bright_cyan": "\033[96m",
    "bright_yellow": "\033[93m",
    "bright_white": "\033[97m",
    "bright_orange": "\033[38;5;208m",
}

# True color (24-bit RGB) — extracted from KH game assets
ANSI_TRUECOLOR = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "green": "\033[38;2;142;188;79m",       # #8EBC4F — KH HP bar green
    "blue": "\033[38;2;24;95;173m",          # #185FAD — KH MP bar blue
    "cyan": "\033[38;2;100;200;220m",        # #64C8DC — KH menu/keyblade cyan
    "yellow": "\033[38;2;248;193;105m",      # #F8C169 — KH munny gold
    "red": "\033[38;2;225;82;57m",           # #E15239 — KH critical/Valor red
    "magenta": "\033[38;2;219;168;205m",     # #DBA8CD — KH MP Charge pink
    "white": "\033[38;2;220;220;230m",       # #DCDCE6 — soft white
    "bright_green": "\033[38;2;160;210;90m", # #A0D25A — brighter KH green
    "bright_blue": "\033[38;2;60;130;210m",  # #3C82D2 — Wisdom Form blue
    "bright_cyan": "\033[38;2;130;220;240m", # #82DCF0 — bright KH cyan
    "bright_yellow": "\033[38;2;255;215;80m",# #FFD750 — Master Form gold
    "bright_white": "\033[38;2;245;245;255m",# #F5F5FF — Final Form silver-white
    "bright_orange": "\033[38;2;240;150;50m",# #F09632 — HP warning amber
}


def _detect_color_mode():
    """Detect terminal color capability.

    Returns 'truecolor', 'basic', or 'none'.
    """
    if os.environ.get("NO_COLOR") is not None:
        return "none"
    if os.environ.get("CLICOLOR") == "0":
        return "none"
    colorterm = os.environ.get("COLORTERM", "")
    if colorterm in ("truecolor", "24bit"):
        return "truecolor"
    return "basic"


def _resolve_ansi(color_mode_override=None):
    """Resolve ANSI color dict based on mode."""
    mode = color_mode_override or _detect_color_mode()
    if mode == "none":
        return {k: "" for k in ANSI_BASIC}
    if mode == "truecolor":
        return dict(ANSI_TRUECOLOR)
    return dict(ANSI_BASIC)


# Initial resolution — may be overridden by config in load_config()
ANSI = _resolve_ansi()

# ─── Unicode Constants ───────────────────────────────────────────

BAR_FULL = "\u2588"    # █ Full block
BAR_EMPTY = "\u2591"   # ░ Light shade (visible empty track)
BAR_BLOCKS = [" ", "\u258f", "\u258e", "\u258d", "\u258c", "\u258b", "\u258a", "\u2589", "\u2588"]
#              0/8    1/8       2/8       3/8       4/8       5/8       6/8       7/8       8/8

KEYBLADE_ICON = "\U0001f5dd"  # 🗝 Old key — keyblades are keys, not swords
MUNNY_ICON = "\u25c9"         # ◉ Fisheye — munny orbs are round jewels
HEART_ICON = "\u2665"         # ♥ Heart — hearts are core KH
MP_ICON = "\u2727"            # ✧ White four-pointed star — magic sparkle
WORLD_ICON = "\u2726"         # ✦ Four-pointed star — worlds glow on the world map
TIMER_ICON = "\u23f1"         # ⏱ Stopwatch — session/journey timer
DRIVE_ICON = "\u25c6"         # ◆ Diamond — the in-game Drive gauge shape
EXP_ICON = "\u265b"           # ♛ Crown — Sora's crown necklace
PARTY_ICON = "\u2666"         # ♦ Diamond suit — party member indicator


# ─── Config Loading ──────────────────────────────────────────────

def load_config():
    """Load config with fallback to defaults."""
    config_dir = os.environ.get(
        "CLAUDE_CONFIG_DIR", os.path.expanduser("~/.claude")
    )
    config_path = os.path.join(config_dir, "hooks", "keyblade", "config.json")

    config = dict(DEFAULT_CONFIG)

    try:
        with open(config_path) as f:
            user_config = json.load(f)
        config.update(user_config)
        # Deep merge nested dicts
        for key in ("colors", "keyblade_names", "drive_form_names", "drive_form_colors"):
            if key in DEFAULT_CONFIG and key in user_config:
                merged = dict(DEFAULT_CONFIG[key])
                merged.update(user_config[key])
                config[key] = merged
    except (FileNotFoundError, json.JSONDecodeError, PermissionError):
        pass

    # Apply color_mode from config (override auto-detection)
    global ANSI
    mode = config.get("color_mode", "auto")
    if mode == "auto":
        ANSI = _resolve_ansi()
    else:
        ANSI = _resolve_ansi(mode)

    return config



# ─── Data Helpers ────────────────────────────────────────────────

USAGE_CACHE_FILE = os.path.join(tempfile.gettempdir(), "keyblade_usage_cache.json")


def resolve_keyblade(model_id, model_display, config):
    """Map model to KH keyblade name."""
    names = config.get("keyblade_names", DEFAULT_CONFIG["keyblade_names"])
    model_lower = ((model_id or "") + " " + (model_display or "")).lower()
    if "opus" in model_lower:
        return names.get("opus", "Ultima Weapon")
    if "sonnet" in model_lower:
        return names.get("sonnet", "Oathkeeper")
    if "haiku" in model_lower:
        return names.get("haiku", "Kingdom Key")
    return "Starlight"


def get_plan_usage(config):
    """Fetch plan usage from Anthropic API with file-based caching."""
    ttl = config.get("hp_usage_cache_ttl", 60)

    # Check cache first
    try:
        with open(USAGE_CACHE_FILE) as f:
            cache = json.load(f)
        if time.time() - cache.get("ts", 0) < ttl:
            return cache.get("five_hour", 0), cache.get("seven_day", 0)
    except (FileNotFoundError, json.JSONDecodeError, KeyError, ValueError):
        pass

    # Extract OAuth token — macOS Keychain or Linux credential file
    try:
        token = ""
        if sys.platform == "darwin":
            r = subprocess.run(
                ["security", "find-generic-password", "-s", "Claude Code-credentials", "-w"],
                capture_output=True, text=True, timeout=5,
            )
            if r.returncode == 0:
                creds = json.loads(r.stdout.strip())
                token = creds.get("claudeAiOauth", {}).get("accessToken", "")
        else:
            # Linux: try reading from Claude Code credential store
            cred_paths = [
                os.path.expanduser("~/.claude/credentials.json"),
                os.path.join(
                    os.environ.get("XDG_CONFIG_HOME", os.path.expanduser("~/.config")),
                    "claude-code", "credentials.json",
                ),
            ]
            for cred_path in cred_paths:
                try:
                    with open(cred_path) as f:
                        creds = json.load(f)
                    token = creds.get("claudeAiOauth", {}).get("accessToken", "")
                    if token:
                        break
                except (FileNotFoundError, json.JSONDecodeError, KeyError):
                    continue
        if not token:
            return 0, 0

        # Call usage API
        req = urllib.request.Request(
            "https://api.anthropic.com/api/oauth/usage",
            headers={
                "Authorization": f"Bearer {token}",
                "anthropic-beta": "oauth-2025-04-20",
            },
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = json.loads(resp.read())

        five_hour = body.get("five_hour", {}).get("utilization", 0) or 0
        seven_day = body.get("seven_day", {}).get("utilization", 0) or 0

        # Write cache
        with open(USAGE_CACHE_FILE, "w") as f:
            json.dump({"ts": time.time(), "five_hour": five_hour, "seven_day": seven_day}, f)

        return five_hour, seven_day
    except (subprocess.SubprocessError, OSError, json.JSONDecodeError,
            KeyError, ValueError, urllib.error.URLError):
        return 0, 0


def calculate_hp(data, config):
    """Calculate HP from configured source. Goes down as usage increases.

    Sources:
      5_hour      — 5-hour plan usage window (Max/Pro)
      7_day       — 7-day plan usage window (Max/Pro)
      cost_budget — session cost vs hp_budget_usd (API key users)
    """
    source = config.get("hp_source", "5_hour")

    if source == "cost_budget":
        budget = config.get("hp_budget_usd", 5.00)
        spent = data.get("cost", {}).get("total_cost_usd", 0) or 0
        if budget <= 0:
            return 100.0
        return max(0.0, min(100.0, (budget - spent) / budget * 100))

    # Plan usage sources (Max/Pro)
    five_hour, seven_day = get_plan_usage(config)
    if source == "7_day":
        return max(0.0, min(100.0, 100.0 - seven_day))
    # Default: 5_hour
    return max(0.0, min(100.0, 100.0 - five_hour))


def calculate_mp(data):
    """Calculate MP from context window remaining percentage."""
    return data.get("context_window", {}).get("remaining_percentage", 100) or 100


def world_and_branch(data, config=None):
    """Return (world_name, branch) separately for responsive display."""
    if config is None:
        config = DEFAULT_CONFIG
    fallback = config.get("world_fallback", "Traverse Town")
    ws = data.get("workspace", {})
    current = ws.get("current_dir", "") or ws.get("project_dir", "")
    if not current:
        return fallback, ""
    dirname = os.path.basename(current)
    if not dirname:
        return fallback, ""

    # Apply world_map: custom name for this directory
    wmap = config.get("world_map", {})
    name = wmap.get(dirname, dirname)

    branch = ""
    try:
        if config.get("show_branch", True):
            r = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True, text=True, cwd=current, timeout=3,
            )
            branch = r.stdout.strip() if r.returncode == 0 else ""
    except (subprocess.SubprocessError, OSError):
        pass

    return name, branch


def world_name(data, config=None):
    """Convert workspace directory to world name with git branch.

    Config options:
      show_branch    — append :branch to world name
      world_fallback — name when no directory found
      world_map      — map directory names to custom names
    """
    name, branch = world_and_branch(data, config)
    if branch:
        return f"{name} \u2219 {branch}"
    return name



def format_duration(ms):
    """Format milliseconds as a journey timer."""
    seconds = int(ms) // 1000
    minutes = seconds // 60
    hours = minutes // 60
    if hours > 0:
        return f"{hours}h{minutes % 60:02d}m"
    if minutes > 0:
        return f"{minutes}m{seconds % 60:02d}s"
    return f"{seconds}s"


def _level_value(data, config):
    """Get the raw value used for level calculation based on level_source."""
    source = config.get("level_source", "lines")
    cost = data.get("cost", {})
    added = cost.get("total_lines_added", 0) or 0
    removed = cost.get("total_lines_removed", 0) or 0
    if source == "added_only":
        return added
    if source == "commits":
        return cost.get("total_commits", 0) or 0
    if source == "files":
        return cost.get("total_files_changed", 0) or 0
    # Default: "lines" (added + removed)
    return added + removed


def calculate_level(data, config=None):
    """Calculate level from configured source and curve.

    Sources: lines (added+removed), added_only, commits, files
    Curves:  linear (every N), exponential (each level costs more)
    """
    if config is None:
        config = DEFAULT_CONFIG
    per = config.get("level_per", 100)
    curve = config.get("level_curve", "linear")
    cap = config.get("level_max", 99)
    value = _level_value(data, config)

    if per <= 0:
        per = 100

    if curve == "exponential":
        # Each level requires `per * level` more (triangular growth)
        # Total for level L = per * (1 + 2 + ... + (L-1)) = per * L*(L-1)/2
        # Solve: value = per * L*(L-1)/2 → L ≈ (1 + sqrt(1 + 8*value/per)) / 2
        level = int((1 + math.sqrt(1 + 8 * value / per)) / 2)
    else:
        # Linear: every `per` units = +1 level
        level = value // per + 1

    return min(level, cap)


def calculate_exp(data, config=None):
    """Calculate EXP — same source as level (lines, added_only, commits, files)."""
    if config is None:
        config = DEFAULT_CONFIG
    return _level_value(data, config)


def calculate_drive(data, config=None):
    """Get uncommitted file and line counts from git.

    Config options:
      drive_include_untracked — count untracked (new) files
    """
    if config is None:
        config = DEFAULT_CONFIG
    ws = data.get("workspace", {})
    work_dir = ws.get("current_dir", "") or ws.get("project_dir", "")
    if not work_dir:
        return 0, 0
    try:
        include_untracked = config.get("drive_include_untracked", True)

        # Count uncommitted files
        r = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, cwd=work_dir, timeout=3,
        )
        if r.returncode == 0 and r.stdout.strip():
            status_lines = [l for l in r.stdout.strip().split("\n") if l.strip()]
            if not include_untracked:
                status_lines = [l for l in status_lines if not l.startswith("??")]
            files = len(status_lines)
        else:
            files = 0

        # Count changed lines (staged + unstaged)
        lines = 0
        for args in [["git", "diff", "--numstat"], ["git", "diff", "--cached", "--numstat"]]:
            r = subprocess.run(args, capture_output=True, text=True, cwd=work_dir, timeout=3)
            for line in r.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                parts = line.split("\t")
                if len(parts) >= 2:
                    try:
                        a = int(parts[0]) if parts[0] != "-" else 0
                        d = int(parts[1]) if parts[1] != "-" else 0
                        lines += a + d
                    except ValueError:
                        pass

        # Count lines in untracked files (git diff can't see these)
        if include_untracked:
            r = subprocess.run(
                ["git", "ls-files", "--others", "--exclude-standard"],
                capture_output=True, text=True, cwd=work_dir, timeout=3,
            )
            if r.returncode == 0 and r.stdout.strip():
                for fpath in r.stdout.strip().split("\n"):
                    if not fpath.strip():
                        continue
                    try:
                        fr = subprocess.run(
                            ["wc", "-l", fpath],
                            capture_output=True, text=True, cwd=work_dir, timeout=2,
                        )
                        if fr.returncode == 0:
                            lines += int(fr.stdout.strip().split()[0])
                    except (subprocess.SubprocessError, OSError, ValueError, IndexError):
                        pass

        return files, lines
    except (subprocess.SubprocessError, OSError):
        return 0, 0


def hp_color(pct):
    """Return ANSI color based on HP percentage."""
    if pct > 50:
        return ANSI["green"]
    if pct > 20:
        return ANSI["bright_orange"]
    return ANSI["red"]


def hp_danger_marker(pct):
    """Return KH-style danger marker for HP percentage."""
    if pct < 15:
        return f" {ANSI['red']}{ANSI['bold']}\033[7m\u300cDANGER\u300d\033[27m{ANSI['reset']}"
    if pct < 20:
        return f" {ANSI['red']}{ANSI['bold']}\u300cDANGER\u300d{ANSI['reset']}"
    if pct <= 50:
        return f" {ANSI['bright_orange']}\u26a0{ANSI['reset']}"
    return ""


def mp_charge_state(mp_pct):
    """Check if MP is in Charge state (KH2 mechanic).

    When MP drops below 10%, the bar enters 'MP CHARGE' mode —
    magenta color with a different label, like KH2.
    """
    return mp_pct < 10


def mp_label_and_color(mp_pct, colors):
    """Return (label, color) for MP bar, handling MP Charge state."""
    if mp_charge_state(mp_pct):
        return f"{MP_ICON} MP", "magenta"
    return f"{MP_ICON} MP", colors.get("mp", "blue")


def mp_charge_marker(mp_pct):
    """Return MP Charge marker if in charge state."""
    if mp_charge_state(mp_pct):
        return f" {ANSI['magenta']}{ANSI['bold']}\u300cMP CHARGE\u300d{ANSI['reset']}"
    return ""


LEVEL_STATE_FILE = os.path.join(tempfile.gettempdir(), "keyblade_level_state.json")
LEVEL_UP_DURATION = 10  # seconds to show level-up notification


def check_level_up(level):
    """Check if level increased since last render. Returns True if leveled up recently."""
    try:
        with open(LEVEL_STATE_FILE) as f:
            state = json.load(f)
        prev_level = state.get("level", 0)
        leveled_at = state.get("ts", 0)
    except (FileNotFoundError, json.JSONDecodeError, KeyError, ValueError):
        prev_level = 0
        leveled_at = 0

    now = time.time()

    if level > prev_level:
        # Level increased — save new state and show notification
        try:
            with open(LEVEL_STATE_FILE, "w") as f:
                json.dump({"level": level, "ts": now}, f)
        except OSError:
            pass
        return True

    if level == prev_level and (now - leveled_at) < LEVEL_UP_DURATION:
        # Still within notification window
        return True

    # Update state without triggering notification
    if level != prev_level:
        try:
            with open(LEVEL_STATE_FILE, "w") as f:
                json.dump({"level": level, "ts": 0}, f)
        except OSError:
            pass

    return False


def level_up_marker(level):
    """Return level-up notification if recently leveled up."""
    if check_level_up(level):
        return f" {ANSI['bright_yellow']}{ANSI['bold']}\u300cLEVEL UP!\u300d{ANSI['reset']}"
    return ""


SAVE_POINT_STATE_FILE = os.path.join(tempfile.gettempdir(), "keyblade_savepoint_state.json")
SAVE_POINT_DURATION = 10  # seconds to show save point notification


def check_save_point(drive_files, drive_lines):
    """Check if working tree just became clean. Returns True within notification window."""
    is_clean = (drive_files == 0 and drive_lines == 0)
    try:
        with open(SAVE_POINT_STATE_FILE) as f:
            state = json.load(f)
        was_clean = state.get("clean", False)
        saved_at = state.get("ts", 0)
    except (FileNotFoundError, json.JSONDecodeError, KeyError, ValueError):
        was_clean = False
        saved_at = 0

    now = time.time()

    if is_clean and not was_clean:
        # Tree just became clean — save state and show notification
        try:
            with open(SAVE_POINT_STATE_FILE, "w") as f:
                json.dump({"clean": True, "ts": now}, f)
        except OSError:
            pass
        return True

    if is_clean and was_clean and (now - saved_at) < SAVE_POINT_DURATION:
        # Still within notification window
        return True

    # Update state if changed
    if is_clean != was_clean:
        try:
            with open(SAVE_POINT_STATE_FILE, "w") as f:
                json.dump({"clean": is_clean, "ts": 0}, f)
        except OSError:
            pass

    return False


def save_point_marker(drive_files, drive_lines):
    """Return Save Point badge if working tree just became clean."""
    if check_save_point(drive_files, drive_lines):
        return f" {ANSI['bright_green']}{ANSI['bold']}\u300cSAVE POINT\u300d{ANSI['reset']}"
    return ""


def is_anti_form(hp_pct, mp_pct, drive_pct):
    """Check if Anti Form should activate (KH2 hidden penalty state).

    Triggers when conditions are dire:
    - HP < 5% AND Drive gauge > 90%, OR
    - Context window (MP) < 5%
    """
    return (hp_pct < 5 and drive_pct > 90) or mp_pct < 5


def resolve_effort_level(data, config=None):
    """Resolve raw effort level string.

    Priority:
      1. Statusbar JSON 'effort' or 'reasoning_effort' (future-proof)
      2. ~/.claude/settings.json 'effortLevel'
      3. CLAUDE_CODE_EFFORT_LEVEL env var
      4. Default: 'high'
    """
    # 1. Check statusbar data (future-proof)
    effort = data.get("effort") or data.get("reasoning_effort")

    # 2. Read from Claude Code settings
    if not effort:
        config_dir = os.environ.get(
            "CLAUDE_CONFIG_DIR", os.path.expanduser("~/.claude")
        )
        settings_path = os.path.join(config_dir, "settings.json")
        try:
            with open(settings_path) as f:
                settings = json.load(f)
            effort = settings.get("effortLevel")
        except (FileNotFoundError, json.JSONDecodeError, PermissionError):
            pass

    # 3. Check environment variable
    if not effort:
        effort = os.environ.get("CLAUDE_CODE_EFFORT_LEVEL")

    # 4. Default to high
    if not effort:
        effort = "high"

    return effort.lower()


def resolve_drive_form(data, config=None):
    """Resolve current Drive Form name from reasoning effort level."""
    if config is None:
        config = DEFAULT_CONFIG
    names = config.get("drive_form_names", DEFAULT_CONFIG["drive_form_names"])
    effort = resolve_effort_level(data, config)
    return names.get(effort, names.get("high", "Master Form"))


def resolve_drive_form_color_name(data, config=None):
    """Get color name for current Drive Form (canonical KH2 colors)."""
    if config is None:
        config = DEFAULT_CONFIG
    effort = resolve_effort_level(data, config)
    form_colors = config.get("drive_form_colors", DEFAULT_CONFIG["drive_form_colors"])
    return form_colors.get(effort, form_colors.get("high", "yellow"))


# ─── Bar Rendering ───────────────────────────────────────────────

def render_bar(label, percentage, width, color, show_pct=True):
    """Render an HP/MP-style bar using smooth Unicode block characters."""
    c = ANSI.get(color, ANSI["green"])
    dim = ANSI["dim"]
    rst = ANSI["reset"]
    bld = ANSI["bold"]

    pct = max(0.0, min(100.0, percentage))
    value = pct / 100.0 * width
    full = int(value)
    partial_idx = round((value - full) * 8)
    if partial_idx == 8:
        full += 1
        partial_idx = 0

    # Build smooth bar — skip partials thinner than 3/8 (visually indistinct from empty)
    partial = BAR_BLOCKS[partial_idx] if partial_idx >= 3 and full < width else ""
    empty = width - full - (1 if partial else 0)

    bar = c + bld + (BAR_FULL * full) + partial + dim + (BAR_EMPTY * max(0, empty)) + rst

    pct_str = f" {pct:.0f}%" if show_pct else ""
    return f"{bld}{c}{label}{rst} [{bar}]{c}{pct_str}{rst}"


# ─── Theme: Classic KH HUD (2 lines) ────────────────────────────

def render_classic(data, config):
    """Classic Kingdom Hearts HUD — HP bar, MP bar, keyblade, munny."""
    hp_pct = calculate_hp(data, config)
    mp_pct = calculate_mp(data)

    model = data.get("model", {})
    keyblade = resolve_keyblade(
        model.get("id", ""), model.get("display_name", ""), config
    )

    cost = data.get("cost", {}).get("total_cost_usd", 0) or 0
    munny = int(cost * 100)

    colors = config.get("colors", DEFAULT_CONFIG["colors"])
    rst = ANSI["reset"]
    bld = ANSI["bold"]

    kc = ANSI.get(colors.get("keyblade", "cyan"), ANSI["cyan"])
    mc = ANSI.get(colors.get("munny", "yellow"), ANSI["yellow"])

    # Drive data (needed for Anti Form + Save Point)
    drive_files, drive_lines = calculate_drive(data, config)
    drive_max = config.get("drive_max_lines", 500)
    drive_pct = min(100.0, (drive_lines / drive_max * 100)) if drive_max > 0 else 0

    # Anti Form check
    if is_anti_form(hp_pct, mp_pct, drive_pct):
        form_name = "Anti Form"
        drive_color_name = "dim"
    else:
        form_name = resolve_drive_form(data, config)
        drive_color_name = resolve_drive_form_color_name(data, config)
    dc = ANSI.get(drive_color_name, ANSI["yellow"])

    # Line 1: MP bar + Keyblade + World
    mp_lbl, mp_clr = mp_label_and_color(mp_pct, colors)
    mp_bar = render_bar(mp_lbl, mp_pct, 12, mp_clr)
    mp_marker = mp_charge_marker(mp_pct)
    line1_parts = [f"  {mp_bar}{mp_marker}  {kc}{KEYBLADE_ICON}  {bld}{keyblade}{rst}"]
    if config.get("show_world", True):
        world = world_name(data, config)
        line1_parts.append(f"{bld}{WORLD_ICON} {world}{rst}")
    line1 = "  ".join(line1_parts)

    # Line 2: HP bar + Save Point + Drive Form + Munny
    color_name = "green"
    if hp_pct <= 50:
        color_name = "bright_orange" if hp_pct > 20 else "red"
    hp_bar = render_bar(f"{HEART_ICON} HP", hp_pct, 20, color_name)
    hp_marker = hp_danger_marker(hp_pct)
    sp_marker = save_point_marker(drive_files, drive_lines)
    line2_parts = [f"  {hp_bar}{hp_marker}{sp_marker}"]
    if config.get("show_drive_form", True):
        line2_parts.append(f"{dc}{DRIVE_ICON} {form_name}{rst}")
    if config.get("show_munny", True):
        line2_parts.append(f"{mc}{MUNNY_ICON} {munny}{rst}")
    line2 = "  ".join(line2_parts)

    return line1 + "\n" + line2


# ─── Theme: Minimal KH (1 line) ─────────────────────────────────

def render_minimal(data, config):
    """Minimal KH — single line, subtle references."""
    hp_pct = calculate_hp(data, config)
    mp_pct = calculate_mp(data)

    model = data.get("model", {})
    keyblade = resolve_keyblade(
        model.get("id", ""), model.get("display_name", ""), config
    )

    cost = data.get("cost", {}).get("total_cost_usd", 0) or 0
    munny = int(cost * 100)

    colors = config.get("colors", DEFAULT_CONFIG["colors"])
    kc = ANSI.get(colors.get("keyblade", "cyan"), ANSI["cyan"])
    mc = ANSI.get(colors.get("munny", "yellow"), ANSI["yellow"])
    mpc = ANSI.get(colors.get("mp", "blue"), ANSI["blue"])
    rst = ANSI["reset"]
    bld = ANSI["bold"]
    dim = ANSI["dim"]

    # Drive data (needed for Anti Form + Save Point)
    drive_files, drive_lines = calculate_drive(data, config)
    drive_max = config.get("drive_max_lines", 500)
    drive_pct = min(100.0, (drive_lines / drive_max * 100)) if drive_max > 0 else 0

    hc = hp_color(hp_pct)
    hp_str = f"{hc}{bld}{hp_pct:.0f}%{rst}" if hp_pct <= 20 else f"{hc}{hp_pct:.0f}%{rst}"
    hp_str += hp_danger_marker(hp_pct)
    hp_str += save_point_marker(drive_files, drive_lines)

    # Anti Form check
    if is_anti_form(hp_pct, mp_pct, drive_pct):
        form_name = "Anti Form"
        drive_color_name = "dim"
    else:
        form_name = resolve_drive_form(data, config)
        drive_color_name = resolve_drive_form_color_name(data, config)
    dc = ANSI.get(drive_color_name, ANSI["yellow"])

    parts = [f"{kc}{KEYBLADE_ICON}  {keyblade}{rst}"]

    if config.get("show_drive_form", True):
        # Strip " Form" suffix for compact display
        short_form = form_name.replace(" Form", "")
        parts.append(f"{dc}{DRIVE_ICON} {short_form}{rst}")

    if config.get("show_world", True):
        world = world_name(data, config)
        parts.append(f"{bld}{WORLD_ICON} {world}{rst}")

    parts.append(f"{HEART_ICON} {hp_str}")
    if mp_charge_state(mp_pct):
        parts.append(f"{ANSI['magenta']}{MP_ICON} {mp_pct:.0f}% \u300cCHARGE\u300d{rst}")
    else:
        parts.append(f"{mpc}{MP_ICON} {mp_pct:.0f}%{rst}")

    if config.get("show_munny", True):
        parts.append(f"{mc}{MUNNY_ICON} {munny}{rst}")

    return "  " + "  ".join(parts)


# ─── Theme: Full RPG (3 lines) ──────────────────────────────────

def render_full_rpg(data, config):
    """Full RPG HUD — HP/MP, keyblade, world, munny, timer, EXP, drive, level."""
    hp_pct = calculate_hp(data, config)
    mp_pct = calculate_mp(data)
    cost_data = data.get("cost", {})
    cost = cost_data.get("total_cost_usd", 0) or 0
    munny = int(cost * 100)

    model = data.get("model", {})
    keyblade = resolve_keyblade(
        model.get("id", ""), model.get("display_name", ""), config
    )

    colors = config.get("colors", DEFAULT_CONFIG["colors"])
    kc = ANSI.get(colors.get("keyblade", "cyan"), ANSI["cyan"])
    mc = ANSI.get(colors.get("munny", "yellow"), ANSI["yellow"])
    rst = ANSI["reset"]
    bld = ANSI["bold"]
    dim = ANSI["dim"]

    exp = calculate_exp(data, config)
    level = calculate_level(data, config)
    drive_files, drive_lines = calculate_drive(data, config)
    duration_ms = cost_data.get("total_duration_ms", 0) or 0

    # Line 1: MP bar (with Charge state) + Keyblade + World
    mp_lbl, mp_clr = mp_label_and_color(mp_pct, colors)
    mp_bar = render_bar(mp_lbl, mp_pct, 12, mp_clr)
    mp_marker = mp_charge_marker(mp_pct)
    world = world_name(data, config)
    line1_parts = [f"  {mp_bar}{mp_marker}  {kc}{KEYBLADE_ICON}  {bld}{keyblade}{rst}"]
    line1_parts.append(f"{bld}{WORLD_ICON} {world}{rst}")
    line1 = "  ".join(line1_parts)

    # Line 2: HP bar + Level + EXP + Level-Up + Save Point
    color_name = "green"
    if hp_pct <= 50:
        color_name = "bright_orange" if hp_pct > 20 else "red"
    hp_bar = render_bar(f"{HEART_ICON} HP", hp_pct, 20, color_name)
    hp_marker = hp_danger_marker(hp_pct)
    lvl_up = level_up_marker(level)
    sp_marker = save_point_marker(drive_files, drive_lines)
    line2_parts = [
        f"  {hp_bar}{hp_marker}",
        f"{bld}LV {level}{rst} ({EXP_ICON} {exp}){lvl_up}{sp_marker}",
    ]
    line2 = "  ".join(line2_parts)

    # Line 3: Drive (uncommitted bar) + Munny + Timer + Party
    drive_width = config.get("drive_bar_width", 10)
    line3_parts = []
    if config.get("show_drive", True):
        drive_max = config.get("drive_max_lines", 500)
        drive_src = config.get("drive_source", "lines")
        if drive_src == "files":
            drive_val = drive_files
        elif drive_src == "both":
            drive_val = drive_files + drive_lines
        else:
            drive_val = drive_lines
        drive_pct = min(100.0, (drive_val / drive_max * 100)) if drive_max > 0 else 0
        # Anti Form check
        if is_anti_form(hp_pct, mp_pct, drive_pct):
            form_name = "Anti Form"
            drive_color_name = "dim"
        elif config.get("show_drive_form", True):
            form_name = resolve_drive_form(data, config)
            drive_color_name = resolve_drive_form_color_name(data, config)
        else:
            form_name = "Drive"
            drive_color_name = resolve_drive_form_color_name(data, config)
        drive_bar = render_bar(f"{DRIVE_ICON} {form_name}", drive_pct, drive_width, drive_color_name)
        line3_parts.append(f"  {drive_bar}")

    if config.get("show_munny", True):
        line3_parts.append(f"{mc}{MUNNY_ICON} {munny}{rst}")

    if config.get("show_timer", True):
        journey = format_duration(duration_ms)
        line3_parts.append(f"{bld}{TIMER_ICON} {journey}{rst}")

    agent = data.get("agent") or {}
    agent_name = agent.get("name", "")
    if agent_name:
        line3_parts.append(f"{PARTY_ICON} {agent_name}")

    line3 = "  ".join(line3_parts)

    return line1 + "\n" + line2 + "\n" + line3


# ─── Main ────────────────────────────────────────────────────────

RENDERERS = {
    "classic": render_classic,
    "minimal": render_minimal,
    "full_rpg": render_full_rpg,
}

FALLBACK = f"{ANSI['cyan']}{KEYBLADE_ICON}  Keyblade{ANSI['reset']}"


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, ValueError):
        print(FALLBACK)
        return

    config = load_config()
    theme = config.get("theme", "classic")
    renderer = RENDERERS.get(theme, render_classic)

    try:
        output = renderer(data, config)
        print(output)
    except Exception:
        print(FALLBACK)


if __name__ == "__main__":
    main()
