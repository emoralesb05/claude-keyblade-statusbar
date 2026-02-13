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
    "hp_usage_cache_ttl": 60,
    "drive_max_lines": 500,
    "keyblade_names": {
        "opus": "Ultima Weapon",
        "sonnet": "Oathkeeper",
        "haiku": "Kingdom Key",
    },
    "show_munny": True,
    "show_world": True,
    "show_timer": True,
    "colors": {
        "hp": "green",
        "mp": "blue",
        "munny": "yellow",
        "keyblade": "cyan",
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
        for key in ("colors", "keyblade_names"):
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

    # Extract OAuth token from macOS Keychain
    try:
        r = subprocess.run(
            ["security", "find-generic-password", "-s", "Claude Code-credentials", "-w"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode != 0:
            return 0, 0
        creds = json.loads(r.stdout.strip())
        token = creds.get("claudeAiOauth", {}).get("accessToken", "")
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
    """Calculate HP from plan usage (5-hour window). Goes down as usage increases."""
    five_hour, _ = get_plan_usage(config)
    return max(0.0, min(100.0, 100.0 - five_hour))


def calculate_mp(data):
    """Calculate MP from context window remaining percentage."""
    return data.get("context_window", {}).get("remaining_percentage", 100) or 100


def world_name(data):
    """Convert workspace directory to world name with git branch and PR."""
    ws = data.get("workspace", {})
    current = ws.get("current_dir", "") or ws.get("project_dir", "")
    if not current:
        return "Traverse Town"
    name = os.path.basename(current)
    if not name:
        return "Traverse Town"

    try:
        r = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, cwd=current, timeout=3,
        )
        branch = r.stdout.strip() if r.returncode == 0 else ""
        if branch:
            name = f"{name}:{branch}"
            # Try to get PR number (best-effort, short timeout)
            r = subprocess.run(
                ["gh", "pr", "view", "--json", "number", "-q", ".number"],
                capture_output=True, text=True, cwd=current, timeout=3,
            )
            pr_num = r.stdout.strip() if r.returncode == 0 else ""
            if pr_num:
                name = f"{name} (#{pr_num})"
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


def calculate_level(data):
    """Calculate level from total lines modified (added + removed). +1 every 100 lines."""
    cost = data.get("cost", {})
    added = cost.get("total_lines_added", 0) or 0
    removed = cost.get("total_lines_removed", 0) or 0
    return (added + removed) // 100 + 1


def calculate_exp(data):
    """Calculate total lines modified (added + removed)."""
    cost = data.get("cost", {})
    added = cost.get("total_lines_added", 0) or 0
    removed = cost.get("total_lines_removed", 0) or 0
    return added + removed


def calculate_drive(data):
    """Get uncommitted file and line counts from git."""
    ws = data.get("workspace", {})
    work_dir = ws.get("current_dir", "") or ws.get("project_dir", "")
    if not work_dir:
        return 0, 0
    try:
        # Count uncommitted files (modified, staged, untracked)
        r = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, cwd=work_dir, timeout=3,
        )
        files = len([l for l in r.stdout.strip().split("\n") if l.strip()]) if r.returncode == 0 else 0

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

    parts = [f"  {kc}{KEYBLADE_ICON} {bld}{keyblade}{rst}"]

    if config.get("show_world", True):
        world = world_name(data)
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

    parts = [f"{kc}{KEYBLADE_ICON} {keyblade}{rst}"]

    if config.get("show_world", True):
        world = world_name(data)
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

    exp = calculate_exp(data)
    level = calculate_level(data)
    drive_files, drive_lines = calculate_drive(data)
    duration_ms = cost_data.get("total_duration_ms", 0) or 0

    # Line 1: HP (plan usage) + MP (context)
    color_name = "green"
    if hp_pct <= 50:
        color_name = "yellow" if hp_pct > 20 else "red"
    hp_bar = render_bar(f"{HEART_ICON} HP", hp_pct, 20, color_name)
    mp_bar = render_bar("MP", mp_pct, 12, colors.get("mp", "blue"))
    line1 = f"  {hp_bar}  {mp_bar}"

    # Line 2: Keyblade + Level + World
    world = world_name(data)
    line2_parts = [
        f"  {kc}{KEYBLADE_ICON} {bld}{keyblade}{rst}",
        f"{bld}Lv.{level}{rst}",
        f"{dim}{WORLD_ICON} {world}{rst}",
    ]
    line2 = "  ".join(line2_parts)

    # Line 3: Drive (uncommitted bar) + EXP + Munny + Timer + Party
    drive_max = config.get("drive_max_lines", 500)
    drive_pct = min(100.0, (drive_lines / drive_max * 100)) if drive_max > 0 else 0
    drive_bar = render_bar(f"{DRIVE_ICON}Drive", drive_pct, 10, "magenta")
    line3_parts = [f"  {drive_bar}"]
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
