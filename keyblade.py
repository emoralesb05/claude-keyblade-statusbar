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

ANSI = {
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
}

# ─── Unicode Constants ───────────────────────────────────────────

BAR_FULL = "\u2588"   # Full block
BAR_EMPTY = "\u2591"  # Light shade

KEYBLADE_ICON = "\u2694"  # Crossed swords
MUNNY_ICON = "\u2b50"     # Star (munny orbs)
HEART_ICON = "\u2665"     # Heart
WORLD_ICON = "\u2299"     # Circled dot (world)
TIMER_ICON = "\u231a"     # Watch
DRIVE_ICON = "\u26a1"     # Lightning (drive form)
EXP_ICON = "\u2605"       # Black star
PARTY_ICON = "\u263a"     # Smiley (party member)


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
        for key in ("colors", "keyblade_names", "drive_form_names"):
            if key in DEFAULT_CONFIG and key in user_config:
                merged = dict(DEFAULT_CONFIG[key])
                merged.update(user_config[key])
                config[key] = merged
    except (FileNotFoundError, json.JSONDecodeError, PermissionError):
        pass

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
    return f"Waypoint ({model_display})" if model_display else "Kingdom Key"


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


def world_name(data, config=None):
    """Convert workspace directory to world name with git branch.

    Config options:
      show_branch    — append :branch to world name
      world_fallback — name when no directory found
      world_map      — map directory names to custom names
    """
    if config is None:
        config = DEFAULT_CONFIG
    fallback = config.get("world_fallback", "Traverse Town")
    ws = data.get("workspace", {})
    current = ws.get("current_dir", "") or ws.get("project_dir", "")
    if not current:
        return fallback
    dirname = os.path.basename(current)
    if not dirname:
        return fallback

    # Apply world_map: custom name for this directory
    wmap = config.get("world_map", {})
    name = wmap.get(dirname, dirname)

    try:
        if config.get("show_branch", True):
            r = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True, text=True, cwd=current, timeout=3,
            )
            branch = r.stdout.strip() if r.returncode == 0 else ""
            if branch:
                name = f"{name}:{branch}"
    except (subprocess.SubprocessError, OSError):
        pass

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
        return ANSI["yellow"]
    return ANSI["red"]


def resolve_drive_form(data, config=None):
    """Resolve current Drive Form name from reasoning effort level.

    Priority:
      1. Statusbar JSON 'effort' or 'reasoning_effort' (future-proof)
      2. ~/.claude/settings.json 'effortLevel'
      3. CLAUDE_CODE_EFFORT_LEVEL env var
      4. Default: 'high' (Master Form)
    """
    if config is None:
        config = DEFAULT_CONFIG
    names = config.get("drive_form_names", DEFAULT_CONFIG["drive_form_names"])

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

    effort = effort.lower()
    return names.get(effort, names.get("high", "Master Form"))


# ─── Bar Rendering ───────────────────────────────────────────────

def render_bar(label, percentage, width, color, show_pct=True):
    """Render an HP/MP-style bar using Unicode block characters."""
    c = ANSI.get(color, ANSI["green"])
    dim = ANSI["dim"]
    rst = ANSI["reset"]
    bld = ANSI["bold"]

    pct = max(0.0, min(100.0, percentage))
    filled = int(pct / 100.0 * width)
    empty = width - filled

    bar = c + bld + (BAR_FULL * filled) + dim + (BAR_EMPTY * empty) + rst

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

    # Line 1: HP (plan usage) + MP (context) bars
    color_name = "green"
    if hp_pct <= 50:
        color_name = "yellow" if hp_pct > 20 else "red"
    hp_bar = render_bar(f"{HEART_ICON} HP", hp_pct, 20, color_name)

    mp_bar = render_bar("MP", mp_pct, 12, colors.get("mp", "blue"))
    line1 = f"  {hp_bar}  {mp_bar}"

    # Line 2: Keyblade + World + Munny
    kc = ANSI.get(colors.get("keyblade", "cyan"), ANSI["cyan"])
    mc = ANSI.get(colors.get("munny", "yellow"), ANSI["yellow"])

    dc = ANSI.get(colors.get("drive", "magenta"), ANSI["magenta"])

    parts = [f"  {kc}{KEYBLADE_ICON} {bld}{keyblade}{rst}"]

    if config.get("show_drive_form", True):
        form = resolve_drive_form(data, config)
        parts.append(f"{dc}{DRIVE_ICON}{form}{rst}")

    if config.get("show_world", True):
        world = world_name(data, config)
        parts.append(f"{ANSI['dim']}{WORLD_ICON} {world}{rst}")

    if config.get("show_munny", True):
        parts.append(f"{mc}{MUNNY_ICON} {munny} munny{rst}")

    line2 = "  ".join(parts)

    return line1 + "\n" + line2


# ─── Theme: Minimal KH (1 line) ─────────────────────────────────

def render_minimal(data, config):
    """Minimal KH — single line, subtle references."""
    hp_pct = calculate_hp(data, config)

    model = data.get("model", {})
    keyblade = resolve_keyblade(
        model.get("id", ""), model.get("display_name", ""), config
    )

    cost = data.get("cost", {}).get("total_cost_usd", 0) or 0
    munny = int(cost * 100)

    colors = config.get("colors", DEFAULT_CONFIG["colors"])
    kc = ANSI.get(colors.get("keyblade", "cyan"), ANSI["cyan"])
    mc = ANSI.get(colors.get("munny", "yellow"), ANSI["yellow"])
    rst = ANSI["reset"]
    bld = ANSI["bold"]
    dim = ANSI["dim"]

    hc = hp_color(hp_pct)
    hp_str = f"{hc}{bld}{hp_pct:.0f}%{rst}" if hp_pct <= 20 else f"{hc}{hp_pct:.0f}%{rst}"

    dc = ANSI.get(colors.get("drive", "magenta"), ANSI["magenta"])

    parts = [f"{kc}{KEYBLADE_ICON} {keyblade}{rst}"]

    if config.get("show_drive_form", True):
        form = resolve_drive_form(data, config)
        # Strip " Form" suffix for compact display
        short_form = form.replace(" Form", "")
        parts.append(f"{dc}{DRIVE_ICON}{short_form}{rst}")

    if config.get("show_world", True):
        world = world_name(data, config)
        parts.append(f"{dim}{WORLD_ICON} {world}{rst}")

    parts.append(f"{HEART_ICON} {hp_str}")

    if config.get("show_munny", True):
        parts.append(f"{mc}{MUNNY_ICON}{munny}{rst}")

    return "  ".join(parts)


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

    # Line 1: HP (plan usage) + MP (context)
    color_name = "green"
    if hp_pct <= 50:
        color_name = "yellow" if hp_pct > 20 else "red"
    hp_bar = render_bar(f"{HEART_ICON} HP", hp_pct, 20, color_name)
    mp_bar = render_bar("MP", mp_pct, 12, colors.get("mp", "blue"))
    line1 = f"  {hp_bar}  {mp_bar}"

    # Line 2: Keyblade + Level + World
    world = world_name(data, config)
    line2_parts = [
        f"  {kc}{KEYBLADE_ICON} {bld}{keyblade}{rst}",
        f"{bld}Lv.{level}{rst}",
        f"{dim}{WORLD_ICON} {world}{rst}",
    ]
    line2 = "  ".join(line2_parts)

    # Line 3: Drive (uncommitted bar) + EXP + Munny + Timer + Party
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
        drive_color = colors.get("drive", "magenta")
        drive_width = config.get("drive_bar_width", 10)
        form_name = resolve_drive_form(data, config) if config.get("show_drive_form", True) else "Drive"
        drive_bar = render_bar(f"{DRIVE_ICON}{form_name}", drive_pct, drive_width, drive_color)
        line3_parts.append(f"  {drive_bar}")
    line3_parts.append(f"{EXP_ICON} {exp} EXP")

    if config.get("show_munny", True):
        line3_parts.append(f"{mc}{MUNNY_ICON}{munny} munny{rst}")

    if config.get("show_timer", True):
        journey = format_duration(duration_ms)
        line3_parts.append(f"{dim}{TIMER_ICON} {journey}{rst}")

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

FALLBACK = f"{ANSI['cyan']}{KEYBLADE_ICON} Keyblade{ANSI['reset']}"


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
