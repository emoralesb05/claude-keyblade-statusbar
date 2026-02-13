#!/usr/bin/env python3
"""keyblade.py — Kingdom Hearts themed statusline for Claude Code."""

import json
import math
import os
import sys

# ─── Configuration ───────────────────────────────────────────────

DEFAULT_CONFIG = {
    "theme": "classic",
    "mp_source": "cost_budget",
    "mp_budget_usd": 5.00,
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


def calculate_mp(data, config):
    """Calculate MP percentage based on configured source."""
    source = config.get("mp_source", "cost_budget")
    if source == "cost_budget":
        budget = config.get("mp_budget_usd", 5.00)
        spent = data.get("cost", {}).get("total_cost_usd", 0) or 0
        if budget <= 0:
            return 100.0
        return max(0.0, min(100.0, (budget - spent) / budget * 100))
    if source == "context_remaining":
        return data.get("context_window", {}).get("remaining_percentage", 100) or 100
    if source == "api_efficiency":
        cost = data.get("cost", {})
        total_ms = cost.get("total_duration_ms", 1) or 1
        api_ms = cost.get("total_api_duration_ms", 0) or 0
        return min(100.0, (api_ms / total_ms) * 100)
    return 100.0


def world_name(data):
    """Convert workspace directory to a KH 'world' name."""
    ws = data.get("workspace", {})
    current = ws.get("current_dir", "") or ws.get("project_dir", "")
    if not current:
        return "Traverse Town"
    name = os.path.basename(current)
    return name if name else "Traverse Town"


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
    """Calculate level from lines added (EXP)."""
    lines = data.get("cost", {}).get("total_lines_added", 0) or 0
    return int(math.sqrt(max(0, lines) / 10)) + 1


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
    ctx = data.get("context_window", {})
    hp_pct = ctx.get("remaining_percentage", 100) or 100
    mp_pct = calculate_mp(data, config)

    model = data.get("model", {})
    keyblade = resolve_keyblade(
        model.get("id", ""), model.get("display_name", ""), config
    )

    cost = data.get("cost", {}).get("total_cost_usd", 0) or 0
    munny = int(cost * 100)

    colors = config.get("colors", DEFAULT_CONFIG["colors"])
    rst = ANSI["reset"]
    bld = ANSI["bold"]

    # Line 1: HP + MP bars
    hp_c = hp_color(hp_pct)
    hp_bar = render_bar(f"{HEART_ICON} HP", hp_pct, 20, "green")
    # Override bar color based on HP level
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
    ctx = data.get("context_window", {})
    hp_pct = ctx.get("remaining_percentage", 100) or 100

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
    ctx = data.get("context_window", {})
    hp_pct = ctx.get("remaining_percentage", 100) or 100
    mp_pct = calculate_mp(data, config)
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

    lines_added = cost_data.get("total_lines_added", 0) or 0
    lines_removed = cost_data.get("total_lines_removed", 0) or 0
    level = calculate_level(data)
    drive_pct = ctx.get("used_percentage", 0) or 0
    duration_ms = cost_data.get("total_duration_ms", 0) or 0

    # Line 1: HP + MP
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

    # Line 3: Drive Gauge + EXP + Munny + Timer + Party
    drive_bar = render_bar(f"{DRIVE_ICON}Drive", drive_pct, 10, "magenta")
    line3_parts = [f"  {drive_bar}"]
    line3_parts.append(f"{EXP_ICON} +{lines_added}/-{lines_removed}")

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
