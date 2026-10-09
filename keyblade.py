#!/usr/bin/env python3
"""keyblade.py — Kingdom Hearts themed statusline for Claude Code.

Modes:
  keyblade.py                                  statusline (Claude Code JSON on stdin)
  keyblade.py --party                          subagent rows for `subagentStatusLine`
  keyblade.py --preview [theme ...] [--width N] render sample scenarios in this terminal
  keyblade.py --register-settings SETTINGS [SCRIPT]
  keyblade.py --unregister-settings SETTINGS
"""

import hashlib
import json
import math
import os
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unicodedata
from urllib.parse import quote

# ─── Configuration ───────────────────────────────────────────────

DEFAULT_CONFIG = {
    "theme": "classic",
    "color_mode": "auto",
    "responsive": True,
    "hyperlinks": True,
    "hp_source": "auto",
    "hp_budget_usd": 5.00,
    "show_hp_reset": True,
    "show_auth": True,
    "auth_cache_ttl": 600,
    "show_drive": True,
    "drive_max_lines": 1000,
    "drive_source": "lines",
    "drive_bar_width": 10,
    "drive_include_untracked": True,
    "git_cache_ttl": 5,
    "level_per": 100,
    "level_curve": "linear",
    "level_max": 99,
    "level_source": "lines",
    "keyblade_names": {
        "opus": "Ultima Weapon",
        "sonnet": "Oathkeeper",
        "haiku": "Kingdom Key",
        "fable": "Sweet Memories",
    },
    "show_munny": True,
    "show_world": True,
    "show_branch": True,
    "show_pr": True,
    "show_worktree": True,
    "show_timer": True,
    "show_focus": True,
    "show_session_name": True,
    "show_fast_mode": True,
    "show_party": True,
    "show_vim_mode": False,
    "party_panel": True,
    "party_members": {},
    "show_drive_form": True,
    "drive_form_names": {
        "low": "Valor Form",
        "medium": "Wisdom Form",
        "high": "Limit Form",
        "xhigh": "Master Form",
        "max": "Final Form",
    },
    "drive_form_colors": {
        "low": "red",
        "medium": "blue",
        "high": "bright_cyan",
        "xhigh": "bright_yellow",
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

# Basic 16-color ANSI (maximum compatibility). No bar-track backgrounds here:
# a solid 16-color background is indistinguishable from the bar fill, so bars
# fall back to a dim ░ track in this mode.
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
    # Frame color
    "frame": "\033[90m",
    # Icon-specific colors
    "icon_heart": "\033[91m",
    "icon_mp": "\033[94m",
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
    # Background colors for bar tracks (darkened versions of foreground)
    "bg_green": "\033[48;2;35;50;20m",        # dark KH green
    "bg_blue": "\033[48;2;8;25;55m",          # dark KH blue
    "bg_cyan": "\033[48;2;20;45;50m",         # dark KH cyan
    "bg_red": "\033[48;2;55;20;15m",          # dark KH red
    "bg_magenta": "\033[48;2;50;35;45m",      # dark KH pink
    "bg_yellow": "\033[48;2;60;50;18m",       # dark KH gold
    "bg_white": "\033[48;2;40;40;45m",        # dark soft white
    "bg_bright_green": "\033[48;2;38;55;22m", # dark bright green
    "bg_bright_blue": "\033[48;2;12;30;55m",  # dark Wisdom Form blue
    "bg_bright_cyan": "\033[48;2;25;50;55m",  # dark Limit Form cyan
    "bg_bright_yellow": "\033[48;2;60;50;18m",# dark Master Form gold
    "bg_bright_white": "\033[48;2;40;40;45m", # dark Final Form
    "bg_bright_orange": "\033[48;2;60;38;12m",# dark HP warning amber
    "bg_dim": "\033[48;2;25;25;25m",          # dark gray (Anti Form)
    # Frame color (muted gray for bar brackets)
    "frame": "\033[38;2;100;100;100m",
    # Icon-specific colors (always the same regardless of bar state)
    "icon_heart": "\033[38;2;255;100;80m",    # bright red heart
    "icon_mp": "\033[38;2;80;150;230m",       # bright blue sparkle
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

BAR_FULL = "█"    # █ Full block
BAR_EMPTY = "░"   # ░ Light shade (visible empty track)
BAR_BLOCKS = [" ", "▏", "▎", "▍", "▌", "▋", "▊", "▉", "█"]
#              0/8    1/8       2/8       3/8       4/8       5/8       6/8       7/8       8/8

KEYBLADE_ICON = "\U0001f5dd"  # 🗝 Old key — keyblades are keys, not swords
MUNNY_ICON = "◉"         # ◉ Fisheye — munny orbs are round jewels
HEART_ICON = "♥"         # ♥ Heart — hearts are core KH
MP_ICON = "✧"            # ✧ White four-pointed star — magic sparkle
WORLD_ICON = "✦"         # ✦ Four-pointed star — worlds glow on the world map
TIMER_ICON = "⏱"         # ⏱ Stopwatch — session/journey timer
DRIVE_ICON = "◆"         # ◆ Diamond — the in-game Drive gauge shape
FORM_ICON = "✶"          # ✶ Six-pointed star — Drive Form transformation aura
EXP_ICON = "♛"           # ♛ Crown — Sora's crown necklace
PARTY_ICON = "♦"         # ♦ Diamond suit — party member indicator
AUTH_ICON = "◈"          # ◈ Diamond in diamond — the gummi you flew in on (auth)
CURE_ICON = "✚"          # ✚ Cure — countdown until the HP window refills
FOCUS_ICON = "◎"         # ◎ Bullseye — KH3 Focus gauge (prompt cache)
JOURNAL_ICON = "✎"       # ✎ Pencil — Jiminy's Journal entry (session name)
HASTE_ICON = "⚡"         # ⚡ High voltage — fast mode
WORKTREE_ICON = "⎇"      # ⎇ Branching path — an alternate world (git worktree)


# ─── Config Loading ──────────────────────────────────────────────

def _valid_config_values(user_config):
    """Drop user values whose type doesn't match the default's, so a stray
    null or string in a hand-edited config can't break every render."""
    valid = {}
    for key, value in user_config.items():
        default = DEFAULT_CONFIG.get(key)
        if key not in DEFAULT_CONFIG:
            ok = True
        elif isinstance(default, bool):
            ok = isinstance(value, bool)
        elif isinstance(default, (int, float)):
            ok = isinstance(value, (int, float)) and not isinstance(value, bool)
        else:
            ok = isinstance(value, type(default))
        if ok:
            valid[key] = value
    return valid


def load_config():
    """Load config with fallback to defaults."""
    config_dir = os.environ.get(
        "CLAUDE_CONFIG_DIR", os.path.expanduser("~/.claude")
    )
    config_path = os.path.join(config_dir, "hooks", "keyblade", "config.json")

    config = dict(DEFAULT_CONFIG)

    try:
        with open(config_path, encoding="utf-8") as f:
            user_config = json.load(f)
    except (OSError, ValueError):
        user_config = {}
    if isinstance(user_config, dict):
        user_config = _valid_config_values(user_config)
        config.update(user_config)
        # Deep merge nested dicts
        for key in ("colors", "keyblade_names", "drive_form_names", "drive_form_colors"):
            if key in user_config:
                merged = dict(DEFAULT_CONFIG[key])
                merged.update(user_config[key])
                config[key] = merged

    # Apply color_mode from config (override auto-detection)
    global ANSI
    mode = config.get("color_mode", "auto")
    if mode == "auto":
        ANSI = _resolve_ansi()
    else:
        ANSI = _resolve_ansi(mode)

    return config


def _claude_settings():
    """Read Claude Code's settings.json (effortLevel, apiKeyHelper, ...)."""
    config_dir = os.environ.get(
        "CLAUDE_CONFIG_DIR", os.path.expanduser("~/.claude")
    )
    try:
        with open(os.path.join(config_dir, "settings.json")) as f:
            settings = json.load(f)
        return settings if isinstance(settings, dict) else {}
    except (OSError, ValueError):
        return {}


# ─── State File ──────────────────────────────────────────────────

STATE_FILE = os.environ.get("KEYBLADE_STATE_FILE") or os.path.join(
    tempfile.gettempdir(), "keyblade_state.json"
)
GIT_CACHE_DIR = tempfile.gettempdir()


def _atomic_write_json(path, obj):
    """Write JSON via temp file + rename so concurrent readers never see a
    torn file (every open session shares the state file)."""
    tmp = None
    try:
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path) or ".", prefix=".keyblade.")
        with os.fdopen(fd, "w") as f:
            json.dump(obj, f)
        os.replace(tmp, path)
    except OSError:
        if tmp:
            try:
                os.unlink(tmp)
            except OSError:
                pass


def _read_state():
    """Read the shared state file. Returns dict."""
    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
        return state if isinstance(state, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_state(state):
    """Write the shared state file."""
    _atomic_write_json(STATE_FILE, state)


def _prune(entries, keep=20):
    """Keep the `keep` most recently stamped entries of a {key: {"ts": ...}} map."""
    if len(entries) <= keep:
        return entries
    def stamp(item):
        value = item[1]
        return value.get("ts", 0) if isinstance(value, dict) else 0
    return dict(sorted(entries.items(), key=stamp, reverse=True)[:keep])


def _project_key(data):
    """Key per-project state by the full workspace path (basenames collide)."""
    return _work_dir(data) or "_default"


def _read_project_state(data):
    """Read per-project state (level_up, save_point)."""
    state = _read_state()
    key = _project_key(data)
    return state.get("projects", {}).get(key, {})


def _write_project_state(data, project_state):
    """Write per-project state, preserving global and other project state.

    Stamped with "ts" so the map can be pruned to recently used projects.
    """
    state = _read_state()
    projects = state.get("projects") or {}
    projects[_project_key(data)] = dict(project_state, ts=time.time())
    state["projects"] = _prune(projects, keep=50)
    _write_state(state)


# ─── Text Helpers ────────────────────────────────────────────────

_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m|\x1b\]8;[^\x07\x1b]*(?:\x07|\x1b\\)")
_CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
RIGHT_MARGIN = 4  # columns left free for notifications that share the row


def visible_width(text):
    """Terminal columns `text` occupies: escape codes are free, wide chars take two."""
    width = 0
    for ch in _ESCAPE_RE.sub("", text):
        if unicodedata.combining(ch) or ch in "‍︎️":
            continue
        width += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return width


def clean_text(text):
    """Strip control characters from payload text before it reaches the terminal."""
    return _CONTROL_RE.sub("", str(text or ""))


def truncate(text, width):
    """Shorten plain text to `width` columns, ending with an ellipsis."""
    if visible_width(text) <= width:
        return text
    out, used = "", 0
    for ch in text:
        w = visible_width(ch)
        if used + w > width - 1:
            break
        out += ch
        used += w
    return out + "…"


def hyperlink(text, url, config=None):
    """Wrap text in an OSC 8 link (Cmd/Ctrl+click) when hyperlinks are enabled."""
    if config is None:
        config = DEFAULT_CONFIG
    url = clean_text(url)
    if not url or not config.get("hyperlinks", True):
        return text
    return f"\033]8;;{url}\a{text}\033]8;;\a"


def format_countdown(seconds):
    """Format seconds until a reset as a compact countdown (3d4h, 2h05m, 12m)."""
    s = max(0, int(seconds))
    days, rem = divmod(s, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days:
        return f"{days}d{hours}h"
    if hours:
        return f"{hours}h{minutes:02d}m"
    return f"{minutes}m" if minutes else "<1m"


def line_budget(config):
    """Usable columns for one statusline row, or None when unknown.

    Claude Code captures the script's output, so tput can't see the terminal;
    it sets COLUMNS instead. Leave a margin for notifications sharing the row.
    """
    if not config.get("responsive", True):
        return None
    try:
        cols = int(os.environ.get("COLUMNS", ""))
    except ValueError:
        return None
    if cols <= 0:
        return None
    return max(20, cols - RIGHT_MARGIN)


def fit_segments(segments, width, prefix="  "):
    """Join segments into one line, dropping the least important until it fits.

    Each segment is (priority, text) or (priority, text, separator); the
    separator (default two spaces) goes before the segment. Higher priority
    numbers drop first, rightmost first among equals; priority 0 never drops.
    """
    segs = [(s[0], s[1], s[2] if len(s) > 2 else "  ") for s in segments if s[1]]

    def join(items):
        return prefix + "".join(
            (sep if i else "") + text for i, (_, text, sep) in enumerate(items)
        )

    line = join(segs)
    while width is not None and visible_width(line) > width:
        droppable = [i for i, s in enumerate(segs) if s[0] > 0]
        if not droppable:
            break
        del segs[max(droppable, key=lambda i: (segs[i][0], i))]
        line = join(segs)
    return line


def bar_widths(budget):
    """(MP, HP) bar widths for the available line width."""
    if budget is None or budget >= 96:
        return 16, 24
    if budget >= 72:
        return 12, 16
    return 8, 10


# ─── Data Helpers ────────────────────────────────────────────────

def _work_dir(data):
    """Current workspace directory from the payload."""
    ws = data.get("workspace") or {}
    return ws.get("current_dir") or ws.get("project_dir") or data.get("cwd") or ""


def _cc_version(data):
    """Claude Code (major, minor) from the payload, or None."""
    m = re.match(r"(\d+)\.(\d+)", str(data.get("version") or ""))
    return (int(m.group(1)), int(m.group(2))) if m else None


def _clamp(pct):
    return max(0.0, min(100.0, float(pct)))


def resolve_keyblade(model_id, model_display, config):
    """Map model to KH keyblade name (any keyblade_names key found in the model)."""
    names = config.get("keyblade_names", DEFAULT_CONFIG["keyblade_names"])
    model_lower = ((model_id or "") + " " + (model_display or "")).lower()
    for family, blade in names.items():
        if family and family.lower() in model_lower:
            return blade
    return "Starlight"


# ─── Auth ────────────────────────────────────────────────────────

# Env vars that decide how Claude Code authenticates. Only their presence is
# fingerprinted — values never leave the environment.
AUTH_ENV_VARS = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "CLAUDE_CODE_OAUTH_TOKEN",
    "CLAUDE_CODE_USE_BEDROCK",
    "CLAUDE_CODE_USE_VERTEX",
    "CLAUDE_CODE_USE_FOUNDRY",
    "ANTHROPIC_BASE_URL",
)
AUTH_ENV_PROVIDERS = (
    ("CLAUDE_CODE_USE_BEDROCK", "bedrock"),
    ("CLAUDE_CODE_USE_VERTEX", "vertex"),
    ("CLAUDE_CODE_USE_FOUNDRY", "foundry"),
)
PROVIDER_LABELS = {
    "bedrock": "Bedrock",
    "vertex": "Vertex",
    "foundry": "Foundry",
    "anthropicAws": "AWS",
    "anthropicGoogleCloud": "Google Cloud",
    "mantle": "Mantle",
    "gateway": "Gateway",
}
AUTH_REFRESH_BACKOFF = 15  # seconds before re-spawning a refresh that hasn't landed


def _truthy_env(name):
    return os.environ.get(name, "").strip().lower() not in ("", "0", "false", "no")


def _auth_fingerprint():
    """Cache key for auth: sessions launched with the same auth env (and config
    dir) authenticate the same way, so /clear doesn't start from scratch."""
    parts = [f"{v}={'1' if os.environ.get(v) else ''}" for v in AUTH_ENV_VARS]
    parts.append(os.environ.get("CLAUDE_CONFIG_DIR", ""))
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:16]


def _claude_executable():
    """Path to the running Claude Code binary, falling back to `claude` on PATH."""
    exe = os.environ.get("CLAUDE_CODE_EXECPATH", "")
    if (exe and os.path.basename(exe).lower() not in ("node", "node.exe", "bun", "bun.exe")
            and os.access(exe, os.X_OK)):
        return exe
    return shutil.which("claude")


def _run_auth_status():
    """Ask Claude Code how it authenticates (`claude auth status --json`).

    Keeps only non-identifying fields (no email or org). None on failure.
    """
    exe = _claude_executable()
    if not exe:
        return None
    try:
        r = subprocess.run(
            [exe, "auth", "status", "--json"],
            capture_output=True, text=True, timeout=10,
        )
        body = json.loads(r.stdout)
    except (subprocess.SubprocessError, OSError, ValueError):
        return None
    if not isinstance(body, dict):
        return None
    keep = ("loggedIn", "authMethod", "apiProvider", "apiKeySource", "subscriptionType")
    return {k: body[k] for k in keep if body.get(k) is not None}


def _auth_from_env():
    """Best-effort guess from the environment while `claude auth status` is
    unavailable or still running."""
    for var, provider in AUTH_ENV_PROVIDERS:
        if _truthy_env(var):
            return {"apiProvider": provider}
    if os.environ.get("ANTHROPIC_API_KEY"):
        return {"authMethod": "api_key", "apiProvider": "firstParty"}
    if os.environ.get("CLAUDE_CODE_OAUTH_TOKEN"):
        return {"authMethod": "oauth_token", "apiProvider": "firstParty"}
    if os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return {"authMethod": "auth_token", "apiProvider": "firstParty"}
    if _claude_settings().get("apiKeyHelper"):
        return {"authMethod": "api_key_helper", "apiProvider": "firstParty"}
    return None


def refresh_auth(key, ttl=None):
    """Run `claude auth status` and cache the result under `key`.

    Runs in a detached child (see _spawn_auth_refresh). On failure the entry
    keeps its previous status and retries in about a minute.
    """
    if ttl is None:
        ttl = DEFAULT_CONFIG["auth_cache_ttl"]
    status = _run_auth_status()
    state = _read_state()
    cache = state.get("auth_cache") or {}
    entry = cache.get(key) if isinstance(cache.get(key), dict) else {}
    now = time.time()
    if status is not None:
        entry = {"ts": now, "status": status}
    else:
        entry = {"ts": now - max(0, ttl - 60), "status": entry.get("status")}
    cache[key] = entry
    state["auth_cache"] = _prune(cache)
    _write_state(state)
    return entry


def _spawn_auth_refresh(key, ttl):
    """Refresh auth in a detached child so a render never waits ~0.3s on it
    (Claude Code cancels a statusline that's still running when the next
    update arrives)."""
    try:
        subprocess.Popen(
            [sys.executable, os.path.abspath(__file__), "--refresh-auth", key, str(ttl)],
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL, start_new_session=True,
        )
    except OSError:
        pass


def resolve_auth(data, config=None):
    """How this session authenticates: {"method", "provider", "plan"}.

    `claude auth status` is authoritative; it's cached per auth environment
    and refreshed in the background (stale-while-revalidate). Until the first
    answer lands, the environment gives a best-effort guess. A payload carrying
    plan rate limits is proof of a claude.ai subscription either way.
    """
    if config is None:
        config = DEFAULT_CONFIG
    ttl = config.get("auth_cache_ttl", 600)
    key = _auth_fingerprint()
    state = _read_state()
    cache = state.get("auth_cache") or {}
    entry = cache.get(key) if isinstance(cache.get(key), dict) else None
    now = time.time()

    expired = entry is None or now - entry.get("ts", 0) >= ttl
    if expired and now - (entry or {}).get("refreshing", 0) > AUTH_REFRESH_BACKOFF and _claude_executable():
        entry = dict(entry or {}, refreshing=now)
        cache[key] = entry
        state["auth_cache"] = _prune(cache)
        _write_state(state)
        _spawn_auth_refresh(key, ttl)
        # Pick up the result if the refresh already landed
        landed = (_read_state().get("auth_cache") or {}).get(key)
        entry = landed if isinstance(landed, dict) else entry

    status = (entry or {}).get("status") or _auth_from_env() or {}
    auth = {
        "method": status.get("authMethod"),
        "provider": status.get("apiProvider"),
        "plan": status.get("subscriptionType"),
    }
    if _plan_windows_from_payload(data) and auth["method"] != "claude.ai":
        auth = {"method": "claude.ai", "provider": "firstParty", "plan": None}
    return auth


def is_subscription(auth):
    """True when the session bills against a claude.ai plan."""
    return bool(auth) and auth.get("method") in ("claude.ai", "oauth_token") \
        and auth.get("provider") in (None, "firstParty")


def auth_badge(auth):
    """Return (label, color_name) for the auth badge, or (None, None) if unknown."""
    if not auth:
        return None, None
    provider = auth.get("provider")
    if provider and provider != "firstParty":
        return PROVIDER_LABELS.get(provider, str(provider).title()), "white"
    method = auth.get("method")
    if method == "claude.ai":
        plan = str(auth.get("plan") or "")
        plan = plan.replace("claude_", "").replace("_", " ").strip()
        return (plan.title() if plan else "Claude.ai"), "bright_cyan"
    if method in ("api_key", "api_key_helper"):
        return "API", "bright_orange"
    if method == "oauth_token":
        return "OAuth", "bright_cyan"
    if method == "auth_token":
        return "Token", "bright_orange"
    return None, None


# ─── HP ──────────────────────────────────────────────────────────

PLAN_WINDOWS = ("five_hour", "seven_day")


def _plan_windows_from_payload(data):
    """Plan usage windows Claude Code sent in this payload."""
    rl = data.get("rate_limits") or {}
    out = {}
    for name in PLAN_WINDOWS:
        w = rl.get(name)
        if isinstance(w, dict) and isinstance(w.get("used_percentage"), (int, float)):
            out[name] = {"used": float(w["used_percentage"]), "resets_at": w.get("resets_at")}
    return out


def get_plan_usage(data):
    """Plan usage windows {name: {"used", "resets_at"}} for claude.ai subscribers.

    Claude Code sends `rate_limits` in the payload, but only after the
    session's first API response. Until then, reuse the last values seen by
    any session (plan usage is account-wide) so HP doesn't flash to 100% on
    startup or after /clear. A window past its resets_at has rolled over.
    """
    windows = _plan_windows_from_payload(data)
    state = _read_state()
    if windows:
        if state.get("usage_cache") != windows:
            state["usage_cache"] = windows
            _write_state(state)
        return windows
    now = time.time()
    cached = state.get("usage_cache") or {}
    return {
        name: w for name, w in cached.items()
        if name in PLAN_WINDOWS and isinstance(w, dict)
        and isinstance(w.get("used"), (int, float))
        and not (isinstance(w.get("resets_at"), (int, float)) and w["resets_at"] <= now)
    }


def _hp_from_window(name, window):
    return {
        "pct": _clamp(100.0 - window["used"]),
        "source": name,
        "resets_at": window.get("resets_at"),
        "spend": None,
    }


def _hp_full(source):
    return {"pct": 100.0, "source": source, "resets_at": None, "spend": None}


def _hp_from_spend_limit(data):
    """HP from a Claude apps gateway spend limit, or None when absent."""
    s = (data.get("rate_limits") or {}).get("spend_limit")
    if not isinstance(s, dict) or not isinstance(s.get("used_percentage"), (int, float)):
        return None
    spend = None
    if isinstance(s.get("used_usd"), (int, float)) and isinstance(s.get("limit_usd"), (int, float)):
        spend = (s["used_usd"], s["limit_usd"])
    return {
        "pct": _clamp(100.0 - s["used_percentage"]),
        "source": "spend_limit",
        "resets_at": s.get("resets_at"),
        "spend": spend,
    }


def _hp_from_budget(data, config):
    budget = config.get("hp_budget_usd", 5.00)
    spent = (data.get("cost") or {}).get("total_cost_usd", 0) or 0
    if budget <= 0:
        return _hp_full("cost_budget")
    return {
        "pct": _clamp((budget - spent) / budget * 100),
        "source": "cost_budget",
        "resets_at": None,
        "spend": None,
    }


def resolve_hp(data, config, auth=None):
    """Resolve HP. Goes down as usage increases.

    Returns {"pct", "source", "resets_at", "spend"}. Sources:
      auto        — subscribers: whichever plan window is closer to its cap;
                    gateway: spend limit; otherwise session cost vs budget
      5_hour      — 5-hour plan usage window (Pro/Max)
      7_day       — 7-day plan usage window (Pro/Max)
      spend_limit — Claude apps gateway spend limit
      cost_budget — session cost vs hp_budget_usd (API key users)
    """
    source = config.get("hp_source", "auto")

    if source == "cost_budget":
        return _hp_from_budget(data, config)

    if source in ("5_hour", "7_day"):
        name = "five_hour" if source == "5_hour" else "seven_day"
        window = get_plan_usage(data).get(name)
        return _hp_from_window(name, window) if window else _hp_full(name)

    if source == "spend_limit":
        return _hp_from_spend_limit(data) or _hp_full("spend_limit")

    # auto
    if not _plan_windows_from_payload(data) and auth is None:
        auth = resolve_auth(data, config)
    if _plan_windows_from_payload(data) or is_subscription(auth):
        windows = get_plan_usage(data)
        if windows:
            name = max(windows, key=lambda n: windows[n]["used"])
            return _hp_from_window(name, windows[name])
    # No plan data: API key / 3P, a Team or Enterprise plan (Claude Code only
    # sends rate_limits to Pro and Max), or a subscriber before any data exists
    return _hp_from_spend_limit(data) or _hp_from_budget(data, config)


def calculate_hp(data, config):
    """HP percentage from the configured source (see resolve_hp)."""
    return resolve_hp(data, config)["pct"]


# ─── MP ──────────────────────────────────────────────────────────

def _read_transcript_context_tokens(transcript_path):
    """Derive current context token count by scanning the transcript tail.

    Claude Code's statusline payload lags one turn behind after /compact and
    may be missing on session start / after /clear. The transcript file is
    the source of truth: the most recent assistant `message.usage` gives the
    real input-token count, and an `isCompactSummary` line marks when /compact
    reset the context.

    Returns total tokens or None if unreadable.
    """
    try:
        with open(transcript_path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            if size == 0:
                return None
            read_size = min(size, 512 * 1024)
            f.seek(size - read_size)
            tail = f.read().decode("utf-8", errors="replace")
    except (OSError, ValueError):
        return None

    lines = [l for l in tail.split("\n") if l.strip()]
    last_usage_tokens = None
    last_usage_idx = -1
    last_compact_idx = -1
    last_compact_obj = None

    for idx, line in enumerate(lines):
        try:
            obj = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            continue
        if obj.get("isCompactSummary"):
            last_compact_idx = idx
            last_compact_obj = obj
        msg = obj.get("message")
        if isinstance(msg, dict):
            u = msg.get("usage")
            if isinstance(u, dict):
                tok = (
                    (u.get("input_tokens") or 0)
                    + (u.get("cache_read_input_tokens") or 0)
                    + (u.get("cache_creation_input_tokens") or 0)
                )
                if tok > 0:
                    last_usage_tokens = tok
                    last_usage_idx = idx

    # Compact marker more recent than the last usage → /compact just ran and
    # the user hasn't taken a turn yet. Estimate from the summary content size.
    if last_compact_obj is not None and last_compact_idx > last_usage_idx:
        content = last_compact_obj.get("message", {}).get("content", "")
        if isinstance(content, list):
            parts = []
            for c in content:
                if isinstance(c, dict):
                    parts.append(c.get("text", "") or "")
                else:
                    parts.append(str(c))
            content = "".join(parts)
        # Rough chars-per-token ≈ 4. Floor at 1000 to avoid absurdly-low reads.
        return max(1000, len(content) // 4)

    return last_usage_tokens


def calculate_mp(data):
    """Calculate MP from context window remaining percentage.

    Prefers scanning the transcript file because the `context_window` field
    in the statusline payload is stale on session start, after /clear, and
    for one turn after /compact.
    """
    ctx = data.get("context_window", {}) or {}
    window_size = ctx.get("context_window_size") or 200_000

    transcript_path = data.get("transcript_path")
    if transcript_path:
        tokens = _read_transcript_context_tokens(transcript_path)
        if tokens is not None and window_size > 0:
            used_pct = min(100.0, tokens / window_size * 100.0)
            return max(0.0, 100.0 - used_pct)

    remaining = ctx.get("remaining_percentage")
    # 0 is a real reading (context full), not "missing"
    return remaining if isinstance(remaining, (int, float)) else 100


# ─── Git ─────────────────────────────────────────────────────────

MAX_UNTRACKED_FILES = 2000      # cap per-render work in repos with huge untracked trees
MAX_UNTRACKED_BYTES = 1 << 20   # read at most 1 MiB per untracked file when counting lines


def _git(work_dir, *args):
    """Run a read-only git command in work_dir. Returns stdout, or None on failure.

    --no-optional-locks keeps `git status` from taking index.lock, which would
    race with git commands Claude is running in the same repo.
    """
    try:
        r = subprocess.run(
            ["git", "--no-optional-locks", "-C", work_dir, *args],
            capture_output=True, encoding="utf-8", errors="replace", timeout=3,
        )
    except (subprocess.SubprocessError, OSError):
        return None
    return r.stdout if r.returncode == 0 else None


def _count_file_lines(path):
    """Count newlines like `wc -l`; binary files count as 0.

    Only regular files: an untracked symlink to a FIFO would block the read
    (and every render after it), and one pointing outside the repo isn't work.
    """
    try:
        if not stat.S_ISREG(os.lstat(path).st_mode):
            return 0
        with open(path, "rb") as f:
            chunk = f.read(MAX_UNTRACKED_BYTES)
    except OSError:
        return 0
    if b"\0" in chunk[:8192]:
        return 0
    return chunk.count(b"\n")


def _sum_numstat(output):
    """Sum added + removed lines from `git diff --numstat` output."""
    total = 0
    for line in (output or "").splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            try:
                total += (int(parts[0]) if parts[0] != "-" else 0) + (int(parts[1]) if parts[1] != "-" else 0)
            except ValueError:
                pass
    return total


def _collect_git_info(work_dir, include_untracked):
    """Branch, ahead/behind and uncommitted file/line counts. None if not a repo."""
    status = _git(
        work_dir, "status", "--porcelain=v2", "--branch", "-z",
        "--untracked-files=" + ("all" if include_untracked else "no"),
    )
    if status is None:
        return None
    info = {"branch": "", "head": "", "ahead": 0, "behind": 0, "files": 0, "lines": 0,
            "untracked": 0, "top": "", "paths": []}
    untracked = []
    paths = []
    entries = status.split("\0")
    i = 0
    while i < len(entries):
        e = entries[i]
        if e.startswith("# branch.oid "):
            info["head"] = e[len("# branch.oid "):]
        elif e.startswith("# branch.head "):
            info["branch"] = e[len("# branch.head "):]
        elif e.startswith("# branch.ab "):
            for part in e[len("# branch.ab "):].split():
                try:
                    n = abs(int(part))
                except ValueError:
                    continue
                info["ahead" if part.startswith("+") else "behind"] = n
        elif e.startswith("1 "):
            info["files"] += 1
            paths.append(e.split(" ", 8)[-1])
        elif e.startswith("2 "):
            info["files"] += 1
            paths.append(e.split(" ", 9)[-1])
            i += 1  # renames/copies carry the original path as an extra field
        elif e.startswith("u "):
            info["files"] += 1
            paths.append(e.split(" ", 10)[-1])
        elif e.startswith("? "):
            info["files"] += 1
            untracked.append(e[2:])
            paths.append(e[2:])
        i += 1
    info["paths"] = paths[:MAX_UNTRACKED_FILES]

    if info["head"] == "(initial)":
        info["head"] = ""
    if info["branch"] == "(detached)":
        info["branch"] = info["head"][:7]

    # Changed lines vs HEAD (staged + unstaged). A repo with no commits yet
    # has no HEAD, so diff the index and the worktree separately.
    # Trailing "--" keeps a file named "head" (case-insensitive FS) from
    # making HEAD ambiguous.
    if info["head"]:
        info["lines"] = _sum_numstat(_git(work_dir, "diff", "HEAD", "--numstat", "--"))
    else:
        info["lines"] = (_sum_numstat(_git(work_dir, "diff", "--cached", "--numstat", "--"))
                         + _sum_numstat(_git(work_dir, "diff", "--numstat", "--")))

    # git diff can't see untracked files; status paths are repo-root relative.
    info["top"] = (_git(work_dir, "rev-parse", "--show-toplevel") or "").strip()
    info["untracked"] = len(untracked)
    for rel in untracked[:MAX_UNTRACKED_FILES]:
        info["lines"] += _count_file_lines(os.path.join(info["top"] or work_dir, rel))
    return info


def git_info(data, config=None):
    """Git state for the workspace, cached for git_cache_ttl seconds.

    Claude Code re-renders on every message, and `git status` in a large repo
    is the slowest thing the statusline does. None outside a git repository.
    """
    if config is None:
        config = DEFAULT_CONFIG
    work_dir = _work_dir(data)
    if not work_dir:
        return None
    include = bool(config.get("drive_include_untracked", True))
    ttl = config.get("git_cache_ttl", 5) or 0
    key = hashlib.sha1(f"{work_dir}\0{include}".encode()).hexdigest()[:16]
    cache_path = os.path.join(GIT_CACHE_DIR, f"keyblade_git_{key}.json")
    if ttl > 0:
        try:
            with open(cache_path) as f:
                cached = json.load(f)
            if cached.get("dir") == work_dir and time.time() - cached.get("ts", 0) < ttl:
                return cached.get("info")
        except (OSError, ValueError, AttributeError):
            pass
    info = _collect_git_info(work_dir, include)
    if ttl > 0:
        _atomic_write_json(cache_path, {"ts": time.time(), "dir": work_dir, "info": info})
    return info


def _dir_basename(data):
    current = _work_dir(data)
    return os.path.basename(current.rstrip("/")) if current else ""


def _world_name(data, config):
    """World name for the workspace directory (world_map aware)."""
    dirname = _dir_basename(data)
    if not dirname:
        return config.get("world_fallback", "Traverse Town")
    return clean_text(config.get("world_map", {}).get(dirname, dirname))


def world_and_branch(data, config=None):
    """Return (world_name, branch) separately for responsive display."""
    if config is None:
        config = DEFAULT_CONFIG
    name = _world_name(data, config)
    if not _dir_basename(data):
        return name, ""
    branch = ""
    if config.get("show_branch", True):
        info = git_info(data, config)
        branch = clean_text(info.get("branch", "")) if info else ""
    return name, branch


def world_name(data, config=None):
    """Convert workspace directory to world name with git branch.

    Config options:
      show_branch    — append ∙ branch to world name
      world_fallback — name when no directory found
      world_map      — map directory names to custom names
    """
    name, branch = world_and_branch(data, config)
    if branch:
        return f"{name} ∙ {branch}"
    return name


def repo_url(data, branch=""):
    """Web URL for the workspace repo (and branch, on known hosts)."""
    repo = (data.get("workspace") or {}).get("repo") or {}
    host, owner, name = repo.get("host"), repo.get("owner"), repo.get("name")
    if not (host and owner and name):
        return ""
    url = f"https://{host}/{owner}/{name}"
    if branch:
        ref = quote(branch, safe="/")
        if "github" in host:
            url += f"/tree/{ref}"
        elif "gitlab" in host:
            url += f"/-/tree/{ref}"
        elif "bitbucket" in host:
            url += f"/src/{ref}"
    return url


def worktree_name(data):
    """Name of the git worktree the session is in, if any."""
    wt = (data.get("worktree") or {}).get("name")
    return clean_text(wt or (data.get("workspace") or {}).get("git_worktree") or "")


def calculate_drive(data, config=None):
    """Get uncommitted file and line counts from git.

    Config options:
      drive_include_untracked — count untracked (new) files
    """
    info = git_info(data, config)
    if not info:
        return 0, 0
    return info["files"], info["lines"]


def _session_progress(data, config):
    """(commits, files) this session, for level_source commits/files.

    Commits: your commits (by user.email) made since the session was first
    seen in this repo, reachable from HEAD — a branch switch or pull doesn't
    count someone else's history. Files: files in those commits, plus files
    dirty now that weren't already dirty when the session started.

    The anchor lives in its own file per (session, repo), so the slow git
    calls here never race the shared state file.
    """
    info = git_info(data, config)
    if info is None or not info.get("top"):
        return 0, 0
    top = info["top"]
    key = hashlib.sha1(f"{data.get('session_id') or '_default'}\0{top}".encode()).hexdigest()[:16]
    path = os.path.join(GIT_CACHE_DIR, f"keyblade_anchor_{key}.json")
    try:
        with open(path, encoding="utf-8") as f:
            anchor = json.load(f)
        if not isinstance(anchor, dict) or not isinstance(anchor.get("start"), (int, float)):
            raise ValueError("bad anchor")
    except (OSError, ValueError):
        email = (_git(top, "config", "user.email") or "").strip()
        anchor = {"start": int(time.time()), "head": info.get("head", ""), "email": email,
                  "baseline": info.get("paths", []), "ts": 0}
        _atomic_write_json(path, anchor)

    now = time.time()
    if now - anchor.get("ts", 0) >= (config.get("git_cache_ttl", 5) or 0):
        commits, committed = 0, set()
        if info.get("head"):
            limits = [f"--since=@{int(anchor['start'])}"]
            if anchor.get("email"):
                limits += [f"--author={anchor['email']}", "--fixed-strings"]
            # --since has 1s resolution, so also exclude what HEAD already held
            # at session start; fall back if that commit is gone (rebase + gc).
            revs = ["HEAD", f"^{anchor['head']}"] if anchor.get("head") else ["HEAD"]
            out = _git(top, "rev-list", "--count", *limits, *revs, "--")
            if out is None and len(revs) > 1:
                revs = ["HEAD"]
                out = _git(top, "rev-list", "--count", *limits, *revs, "--")
            out = (out or "").strip()
            commits = int(out) if out.isdigit() else 0
            if commits:
                log = _git(top, "log", *limits, "--name-only", "--format=", *revs, "--")
                committed = {l for l in (log or "").splitlines() if l.strip()}
        fresh = set(info.get("paths", [])) - set(anchor.get("baseline", []))
        anchor.update(commits=commits, files=len(committed | fresh), ts=now)
        _atomic_write_json(path, anchor)
    return anchor.get("commits", 0), anchor.get("files", 0)


# ─── Level & EXP ─────────────────────────────────────────────────

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
    cost = data.get("cost") or {}
    added = cost.get("total_lines_added", 0) or 0
    removed = cost.get("total_lines_removed", 0) or 0
    if source == "added_only":
        return added
    if source in ("commits", "files"):
        commits, files = _session_progress(data, config)
        return commits if source == "commits" else files
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


# ─── Markers ─────────────────────────────────────────────────────

def hp_color(pct, base="green"):
    """Return ANSI color based on HP percentage."""
    return ANSI.get(hp_bar_color(pct, {"hp": base}), ANSI["green"])


def hp_bar_color(pct, colors):
    """Color name for the HP bar: colors.hp when healthy, amber/red when low."""
    if pct > 50:
        return colors.get("hp", "green")
    if pct > 20:
        return "bright_orange"
    return "red"


def hp_danger_marker(pct):
    """Return KH-style danger marker for HP percentage."""
    if pct < 15:
        return f" {ANSI['red']}{ANSI['bold']}\033[7m「DANGER」\033[27m{ANSI['reset']}"
    if pct < 20:
        return f" {ANSI['red']}{ANSI['bold']}「DANGER」{ANSI['reset']}"
    if pct <= 50:
        return f" {ANSI['bright_orange']}⚠{ANSI['reset']}"
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
        return "MP", "magenta"
    return "MP", colors.get("mp", "blue")


def mp_charge_marker(mp_pct):
    """Return MP Charge marker if in charge state."""
    if mp_charge_state(mp_pct):
        return f" {ANSI['magenta']}{ANSI['bold']}「MP CHARGE」{ANSI['reset']}"
    return ""


LEVEL_UP_DURATION = 10  # seconds to show level-up notification


def _level_key(data):
    """Level comes from per-session counters, so level-up state is per session
    (two sessions in one repo would otherwise flip each other's badge)."""
    return data.get("session_id") or _project_key(data)


def _write_level_state(data, level, leveled_at):
    """Store {"level", "at": level-up time, "ts": last write (for pruning)}."""
    state = _read_state()
    levels = state.get("levels") or {}
    levels[_level_key(data)] = {"level": level, "at": leveled_at, "ts": time.time()}
    state["levels"] = _prune(levels, keep=50)
    _write_state(state)


def check_level_up(level, data=None):
    """Check if level increased since last render. Returns True if leveled up recently."""
    if data is None:
        data = {}
    lvl_state = (_read_state().get("levels") or {}).get(_level_key(data), {})
    prev_level = lvl_state.get("level", 0)
    leveled_at = lvl_state.get("at", 0)

    now = time.time()

    if level > prev_level:
        _write_level_state(data, level, now)
        return True

    if level == prev_level and (now - leveled_at) < LEVEL_UP_DURATION:
        return True

    if level != prev_level:
        _write_level_state(data, level, 0)

    return False


def level_up_marker(level, data=None):
    """Return level-up notification if recently leveled up."""
    if check_level_up(level, data):
        return f" {ANSI['bright_yellow']}{ANSI['bold']}「LEVEL UP!」{ANSI['reset']}"
    return ""


SAVE_POINT_DURATION = 10  # seconds to show save point notification


def check_save_point(drive_files, drive_lines, data=None):
    """Check if working tree just became clean. Returns True within notification window."""
    if data is None:
        data = {}
    is_clean = (drive_files == 0 and drive_lines == 0)
    pstate = _read_project_state(data)
    sp_state = pstate.get("save_point", {})
    was_clean = sp_state.get("clean", False)
    saved_at = sp_state.get("ts", 0)

    now = time.time()

    if is_clean and not was_clean:
        pstate["save_point"] = {"clean": True, "ts": now}
        _write_project_state(data, pstate)
        return True

    if is_clean and was_clean and (now - saved_at) < SAVE_POINT_DURATION:
        return True

    if is_clean != was_clean:
        pstate["save_point"] = {"clean": is_clean, "ts": 0}
        _write_project_state(data, pstate)

    return False


def save_point_marker(drive_files, drive_lines, data=None):
    """Return Save Point badge if working tree just became clean."""
    if check_save_point(drive_files, drive_lines, data):
        return f" {ANSI['bright_green']}{ANSI['bold']}「SAVE POINT」{ANSI['reset']}"
    return ""


def is_anti_form(hp_pct, mp_pct, drive_pct):
    """Check if Anti Form should activate (KH2 hidden penalty state).

    Triggers when conditions are dire:
    - HP < 5% AND Drive gauge > 90%, OR
    - Context window (MP) < 5%
    """
    return (hp_pct < 5 and drive_pct > 90) or mp_pct < 5


# ─── Effort / Drive Form ─────────────────────────────────────────

def resolve_effort_level(data, config=None):
    """Resolve raw effort level string, or None when the model has no effort.

    Priority:
      1. Payload `effort.level` (live — follows mid-session /effort changes)
      2. ~/.claude/settings.json 'effortLevel'
      3. CLAUDE_CODE_EFFORT_LEVEL env var
      4. Default: 'high'

    Claude Code v2.1+ omits `effort` when the current model doesn't support
    the effort parameter (e.g. Haiku); that returns None instead of falling
    back to settings.
    """
    effort = data.get("effort") or data.get("reasoning_effort")

    # Claude Code v2.1+ wraps effort as {"level": "..."}; older versions
    # and settings.json still use a plain string.
    if isinstance(effort, dict):
        effort = effort.get("level")

    if not effort and (_cc_version(data) or (0, 0)) >= (2, 1):
        return None

    if not effort:
        effort = _claude_settings().get("effortLevel")

    if not effort:
        effort = os.environ.get("CLAUDE_CODE_EFFORT_LEVEL")

    if not effort:
        effort = "high"

    return str(effort).lower()


def resolve_drive_form(data, config=None):
    """Resolve current Drive Form name from reasoning effort level (None if no effort)."""
    if config is None:
        config = DEFAULT_CONFIG
    names = config.get("drive_form_names", DEFAULT_CONFIG["drive_form_names"])
    effort = resolve_effort_level(data, config)
    if effort is None:
        return None
    return names.get(effort, names.get("high", "Master Form"))


def resolve_drive_form_color_name(data, config=None):
    """Get color name for current Drive Form (canonical KH2 colors)."""
    if config is None:
        config = DEFAULT_CONFIG
    effort = resolve_effort_level(data, config)
    if effort is None:
        return config.get("colors", DEFAULT_CONFIG["colors"]).get("drive", "magenta")
    form_colors = config.get("drive_form_colors", DEFAULT_CONFIG["drive_form_colors"])
    return form_colors.get(effort, form_colors.get("high", "yellow"))


# ─── Bar Rendering ───────────────────────────────────────────────

def render_bar(percentage, width, color, show_pct=True, icon="", icon_color=""):
    """Render a KH-style bar with background track and icon.

    Args:
        percentage: Fill percentage (0-100)
        width: Bar width in characters
        color: Color name for the fill (key in ANSI dict)
        show_pct: Show percentage text after bar
        icon: Icon character (e.g. HEART_ICON) — rendered in its own color
        icon_color: ANSI key for icon color (e.g. "icon_heart")
    """
    c = ANSI.get(color, ANSI["green"])
    rst = ANSI["reset"]
    bld = ANSI["bold"]
    bg = ANSI.get(f"bg_{color}", "")

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

    # Fill portion in bar color, empty portion with background-colored track
    fill_part = c + bld + (BAR_FULL * full) + partial
    if bg:
        empty_part = bg + (" " * max(0, empty)) + rst
    else:
        # Drop the fill's bold first — bold+dim renders at normal intensity
        empty_part = rst + c + ANSI["dim"] + (BAR_EMPTY * max(0, empty)) + rst

    bar = fill_part + empty_part

    # Icon in its own color, no brackets, no label text
    ic = ANSI.get(icon_color, c) if icon_color else c
    icon_str = f"{ic}{icon}{rst} " if icon else ""
    pct_str = f" {pct:.0f}%" if show_pct else ""
    return f"{icon_str}{bar}{c}{pct_str}{rst}"


# ─── Segments ────────────────────────────────────────────────────

PR_STATES = {
    "approved": ("✓", "green"),             # ✓
    "changes_requested": ("✗", "red"),      # ✗
    "pending": ("○", "yellow"),             # ○
    "draft": ("◌", "dim"),                  # ◌
}


def gather(data, config, auth=None):
    """Compute the values every theme draws from, once per render."""
    colors = config.get("colors", DEFAULT_CONFIG["colors"])
    if auth is None and (config.get("show_auth", True) or config.get("hp_source", "auto") == "auto"):
        auth = resolve_auth(data, config)
    hp = resolve_hp(data, config, auth)
    mp = calculate_mp(data)
    model = data.get("model") or {}
    cost = data.get("cost") or {}
    info = git_info(data, config)
    files, lines = (info["files"], info["lines"]) if info else (0, 0)

    drive_src = config.get("drive_source", "lines")
    if drive_src == "files":
        drive_val = files
    elif drive_src == "both":
        drive_val = files + lines
    else:
        drive_val = lines
    drive_max = config.get("drive_max_lines", 1000)
    drive_pct = min(100.0, drive_val / drive_max * 100) if drive_max > 0 else 0.0

    if is_anti_form(hp["pct"], mp, drive_pct):
        form, form_color = "Anti Form", "dim"
    else:
        form = resolve_drive_form(data, config)
        form_color = resolve_drive_form_color_name(data, config)

    return {
        "data": data,
        "config": config,
        "colors": colors,
        "auth": auth,
        "hp": hp,
        "mp": mp,
        "keyblade": resolve_keyblade(model.get("id"), model.get("display_name"), config),
        "munny": int((cost.get("total_cost_usd") or 0) * 100),
        "duration_ms": cost.get("total_duration_ms") or 0,
        "git": info,
        "drive_files": files,
        "drive_lines": lines,
        "drive_pct": drive_pct,
        "form": form,
        "form_color": form_color,
        "budget": line_budget(config),
    }


def seg_mp(hud, width):
    mp = hud["mp"]
    _, clr = mp_label_and_color(mp, hud["colors"])
    return render_bar(mp, width, clr, icon=MP_ICON, icon_color="icon_mp") + mp_charge_marker(mp)


def seg_hp(hud, width):
    hp = hud["hp"]["pct"]
    bar = render_bar(hp, width, hp_bar_color(hp, hud["colors"]), icon=HEART_ICON, icon_color="icon_heart")
    return bar + hp_danger_marker(hp)


def seg_keyblade(hud, bold=True):
    kc = ANSI.get(hud["colors"].get("keyblade", "cyan"), ANSI["cyan"])
    text = f"{kc}{KEYBLADE_ICON}  {ANSI['bold'] if bold else ''}{hud['keyblade']}{ANSI['reset']}"
    if hud["config"].get("show_fast_mode", True) and hud["data"].get("fast_mode"):
        text += f" {ANSI['bright_yellow']}{HASTE_ICON}{ANSI['reset']}"
    return text


def seg_auth(hud):
    if not hud["config"].get("show_auth", True):
        return ""
    label, color = auth_badge(hud["auth"])
    if not label:
        return ""
    return f"{ANSI.get(color, '')}{AUTH_ICON} {label}{ANSI['reset']}"


def world_segments(hud, prio=2):
    """World name (linked to the repo), extra dirs, branch with ahead/behind, worktree."""
    data, config = hud["data"], hud["config"]
    if not config.get("show_world", True):
        return []
    bld, rst, dim = ANSI["bold"], ANSI["reset"], ANSI["dim"]
    name = _world_name(data, config)
    if hud["budget"] is not None:
        # Shorten long directory names on narrow terminals rather than drop the world
        name = truncate(name, max(12, hud["budget"] // 3))
    info = hud["git"] or {}
    branch = clean_text(info.get("branch", "")) if config.get("show_branch", True) else ""
    segs = [(prio, f"{bld}{WORLD_ICON} {hyperlink(name, repo_url(data, branch), config)}{rst}")]
    added = len((data.get("workspace") or {}).get("added_dirs") or [])
    if added:
        segs.append((prio + 3, f"{dim}+{added}{rst}", " "))
    if branch:
        ab = ""
        if info.get("ahead"):
            ab += f"↑{info['ahead']}"
        if info.get("behind"):
            ab += f"↓{info['behind']}"
        segs.append((prio + 2, f"{bld}{branch}{rst}" + (f" {dim}{ab}{rst}" if ab else ""), f" {bld}∙{rst} "))
    worktree = worktree_name(data)
    if worktree and config.get("show_worktree", True):
        segs.append((prio + 2, f"{dim}{WORKTREE_ICON} {worktree}{rst}", " "))
    return segs


def seg_pr(hud):
    """Open PR/MR number, colored and marked by review state, linked to the PR."""
    pr = hud["data"].get("pr") or {}
    number = pr.get("number")
    if not number or not hud["config"].get("show_pr", True):
        return ""
    prefix = "!" if pr.get("kind") == "mr" else "#"
    glyph, color = PR_STATES.get(pr.get("review_state"), ("", "white"))
    text = f"{prefix}{clean_text(number)}" + (f" {glyph}" if glyph else "")
    return f"{ANSI.get(color, '')}{hyperlink(text, pr.get('url'), hud['config'])}{ANSI['reset']}"


def seg_cure(hud):
    """Countdown until the HP window resets (KH Cure)."""
    resets_at = hud["hp"].get("resets_at")
    now = time.time()
    if not hud["config"].get("show_hp_reset", True) or not isinstance(resets_at, (int, float)) or resets_at <= now:
        return ""
    return f"{ANSI['green']}{CURE_ICON} {format_countdown(resets_at - now)}{ANSI['reset']}"


def seg_spend(hud):
    """Gateway spend vs limit, when HP comes from a spend limit."""
    spend = hud["hp"].get("spend")
    if not spend:
        return ""
    used, limit = spend
    mc = ANSI.get(hud["colors"].get("munny", "yellow"), ANSI["yellow"])
    return f"{mc}${used:,.0f}/${limit:,.0f}{ANSI['reset']}"


def seg_save_point(hud):
    if hud["git"] is None:
        return ""
    return save_point_marker(hud["drive_files"], hud["drive_lines"], hud["data"]).lstrip(" ")


def seg_form(hud, short=False):
    if not hud["form"] or not hud["config"].get("show_drive_form", True):
        return ""
    name = hud["form"].replace(" Form", "") if short else hud["form"]
    return f"{ANSI.get(hud['form_color'], ANSI['yellow'])}{FORM_ICON} {name}{ANSI['reset']}"


def seg_munny(hud):
    if not hud["config"].get("show_munny", True):
        return ""
    mc = ANSI.get(hud["colors"].get("munny", "yellow"), ANSI["yellow"])
    return f"{mc}{MUNNY_ICON} {hud['munny']}{ANSI['reset']}"


def seg_party(hud):
    name = clean_text((hud["data"].get("agent") or {}).get("name", ""))
    if not name or not hud["config"].get("show_party", True):
        return ""
    return f"{PARTY_ICON} {name}"


def seg_session(hud):
    name = clean_text(hud["data"].get("session_name", ""))
    if not name or not hud["config"].get("show_session_name", True):
        return ""
    return f"{ANSI['dim']}{JOURNAL_ICON} {truncate(name, 28)}{ANSI['reset']}"


def seg_focus(hud):
    """KH3 Focus gauge: prompt cache hit ratio, and time until a warm cache goes cold."""
    pc = hud["data"].get("prompt_cache")
    if not isinstance(pc, dict) or not pc.get("caching_observed") or not hud["config"].get("show_focus", True):
        return ""
    ratio = pc.get("hit_ratio")
    pct = f"{ratio * 100:.0f}%" if isinstance(ratio, (int, float)) else "—"
    if not pc.get("warm"):
        return f"{ANSI['dim']}{FOCUS_ICON} {pct} cold{ANSI['reset']}"
    expires = pc.get("expires_at")
    now = time.time()
    tail = f" {format_countdown(expires - now)}" if isinstance(expires, (int, float)) and expires > now else ""
    return f"{ANSI['cyan']}{FOCUS_ICON} {pct}{ANSI['dim']}{tail}{ANSI['reset']}"


def seg_timer(hud):
    if not hud["config"].get("show_timer", True):
        return ""
    return f"{ANSI['bold']}{TIMER_ICON} {format_duration(hud['duration_ms'])}{ANSI['reset']}"


def seg_vim(hud):
    mode = clean_text((hud["data"].get("vim") or {}).get("mode", ""))
    if not mode or not hud["config"].get("show_vim_mode", False):
        return ""
    return f"{ANSI['dim']}-- {mode} --{ANSI['reset']}"


# ─── Theme: Classic KH HUD (2 lines) ────────────────────────────

def render_classic(data, config, auth=None):
    """Classic Kingdom Hearts HUD — HP bar, MP bar, keyblade, munny."""
    hud = gather(data, config, auth)
    budget = hud["budget"]
    mp_w, hp_w = bar_widths(budget)

    # Line 1: MP bar + Keyblade + Auth + World + PR
    line1 = fit_segments([
        (0, seg_mp(hud, mp_w)),
        (0, seg_keyblade(hud)),
        (3, seg_auth(hud)),
        *world_segments(hud),
        (4, seg_pr(hud)),
    ], budget)

    # Line 2: HP bar + Cure + Save Point + Drive Form + Munny + Party
    line2 = fit_segments([
        (0, seg_hp(hud, hp_w)),
        (3, seg_spend(hud), " "),
        (5, seg_cure(hud), " "),
        (1, seg_save_point(hud), " "),
        (2, seg_form(hud)),
        (3, seg_munny(hud)),
        (4, seg_party(hud)),
        (6, seg_session(hud)),
        (2, seg_vim(hud)),
    ], budget)

    return line1 + "\n" + line2


# ─── Theme: Minimal KH (1 line) ─────────────────────────────────

def render_minimal(data, config, auth=None):
    """Minimal KH — single line, subtle references."""
    hud = gather(data, config, auth)
    colors = hud["colors"]
    rst = ANSI["reset"]
    bld = ANSI["bold"]

    hp_pct, mp_pct = hud["hp"]["pct"], hud["mp"]
    hc = hp_color(hp_pct, colors.get("hp", "green"))
    hp_str = f"{hc}{bld}{hp_pct:.0f}%{rst}" if hp_pct <= 20 else f"{hc}{hp_pct:.0f}%{rst}"
    hp_str += hp_danger_marker(hp_pct)

    if mp_charge_state(mp_pct):
        mp_str = f"{ANSI['magenta']}{MP_ICON} {mp_pct:.0f}% 「CHARGE」{rst}"
    else:
        mpc = ANSI.get(colors.get("mp", "blue"), ANSI["blue"])
        mp_str = f"{mpc}{MP_ICON} {mp_pct:.0f}%{rst}"

    return fit_segments([
        (0, seg_keyblade(hud, bold=False)),
        (3, seg_auth(hud)),
        (2, seg_form(hud, short=True)),
        *world_segments(hud, prio=3),
        (4, seg_pr(hud)),
        (0, f"{HEART_ICON} {hp_str}"),
        (3, seg_spend(hud), " "),
        (6, seg_cure(hud), " "),
        (1, seg_save_point(hud), " "),
        (0, mp_str),
        (2, seg_munny(hud)),
        (5, seg_party(hud)),
        (2, seg_vim(hud)),
    ], hud["budget"])


# ─── Theme: Full RPG (3 lines) ──────────────────────────────────

def render_full_rpg(data, config, auth=None):
    """Full RPG HUD — HP/MP, keyblade, world, munny, timer, EXP, drive, level."""
    hud = gather(data, config, auth)
    budget = hud["budget"]
    mp_w, hp_w = bar_widths(budget)
    rst = ANSI["reset"]
    bld = ANSI["bold"]

    level = calculate_level(data, config)
    exp = calculate_exp(data, config)

    # Line 1: MP bar (with Charge state) + Keyblade + Auth + World + PR
    line1 = fit_segments([
        (0, seg_mp(hud, mp_w)),
        (0, seg_keyblade(hud)),
        (3, seg_auth(hud)),
        *world_segments(hud),
        (4, seg_pr(hud)),
    ], budget)

    # Line 2: HP bar + Cure + Level + EXP + Level-Up + Save Point
    line2 = fit_segments([
        (0, seg_hp(hud, hp_w)),
        (3, seg_spend(hud), " "),
        (5, seg_cure(hud), " "),
        (1, f"{bld}LV {level}{rst} ({EXP_ICON} {exp})"),
        (1, level_up_marker(level, data).lstrip(" "), " "),
        (1, seg_save_point(hud), " "),
    ], budget)

    # Line 3: Drive (uncommitted bar) + Munny + Focus + Timer + Party + Journal
    line3_segs = []
    if config.get("show_drive", True):
        if hud["form"] == "Anti Form" or (hud["form"] and config.get("show_drive_form", True)):
            form_name, drive_color = hud["form"], hud["form_color"]
        else:
            form_name, drive_color = "Drive", hud["colors"].get("drive", "magenta")
        drive_w = config.get("drive_bar_width", 10)
        if budget is not None and budget < 72:
            drive_w = min(drive_w, 8)
        drive_bar = render_bar(hud["drive_pct"], drive_w, drive_color, icon=DRIVE_ICON)
        dc = ANSI.get(drive_color, ANSI["yellow"])
        line3_segs.append((0, f"{drive_bar}  {dc}{FORM_ICON} {form_name}{rst}"))
    else:
        line3_segs.append((2, seg_form(hud)))
    line3_segs += [
        (2, seg_munny(hud)),
        (4, seg_focus(hud)),
        (3, seg_timer(hud)),
        (3, seg_party(hud)),
        (5, seg_session(hud)),
        (2, seg_vim(hud)),
    ]
    line3 = fit_segments(line3_segs, budget)

    return line1 + "\n" + line2 + "\n" + line3


# ─── Party Panel (subagentStatusLine) ────────────────────────────

# Subagents join the party as real KH party members, picked by role. Role
# words match the subagent's type/name as words ("code-reviewer" → review);
# keys under 4 letters must match a whole word ("pr", not "prompt").
PARTY_ROLES = (
    ("security", "Donald"), ("audit", "Donald"),        # defensive magic
    ("test", "Goofy"), ("qa", "Goofy"),                 # the shield: reliable support
    ("review", "Riku"),                                 # the rival's sharp eye
    ("explore", "Aladdin"), ("search", "Aladdin"),      # knows every corner of Agrabah
    ("plan", "Mulan"), ("architect", "Mulan"),          # the strategist
    ("debug", "Tron"), ("investigat", "Tron"),          # fights the bugs in the system
    ("docs", "Beast"), ("documentation", "Beast"),      # keeper of the library
    ("writer", "Beast"),
    ("pr", "Jack Sparrow"), ("release", "Jack Sparrow"),  # ships it
    ("deploy", "Jack Sparrow"),
)
# World guests for everything else (and for a second explorer, reviewer, ...)
PARTY_GUESTS = ("Simba", "Auron", "Ariel", "Tarzan", "Hercules", "Rapunzel",
                "Baymax", "Sulley", "Peter Pan", "Woody")
PARTY_COLORS = {
    "Donald": "bright_blue", "Goofy": "bright_green", "Riku": "bright_white",
    "Aladdin": "bright_orange", "Mulan": "red", "Tron": "bright_cyan",
    "Beast": "magenta", "Jack Sparrow": "yellow", "Simba": "bright_yellow",
    "Auron": "red", "Ariel": "cyan", "Tarzan": "green", "Hercules": "bright_yellow",
    "Rapunzel": "magenta", "Baymax": "white", "Sulley": "blue",
    "Peter Pan": "bright_green", "Woody": "yellow",
}
PARTY_TWINKLE = ("✦", "✧")   # ✦ ✧ alternate each tick while working
PARTY_HP_WARN = 25                     # show ♥ only when context left drops below this %


def _role_words(*names):
    """Lowercase words of agent type/name strings, splitting camelCase."""
    words = []
    for name in names:
        spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(name or ""))
        words += re.findall(r"[a-z0-9]+", spaced.lower())
    return words


def _role_matches(key, words):
    key = key.lower()
    return any(w == key or (len(key) >= 4 and w.startswith(key)) for w in words)


def party_role_member(task, config):
    """Party member for a subagent's role (config party_members first), or None."""
    agent_type, name = task.get("agentType") or "", task.get("name") or ""
    words = _role_words(agent_type, name)
    for key, member in (config.get("party_members") or {}).items():
        if key.lower() in (agent_type.lower(), name.lower()) or _role_matches(key, words):
            return clean_text(member)
    for key, member in PARTY_ROLES:
        if _role_matches(key, words):
            return member
    return None


def assign_party(tasks, config, now):
    """Give each visible subagent a party member, stable for its lifetime.

    Assignments live in the state file so a member doesn't change when an
    earlier subagent leaves the panel; two visible subagents never share one.
    Also records when each subagent first shows up finished, for its time.
    """
    state = _read_state()
    party = state.get("party") or {}
    party = {k: v for k, v in party.items() if isinstance(v, dict)}
    taken = {party[t["id"]].get("member") for t in tasks if t["id"] in party}
    changed = False
    for task in tasks:
        if task["id"] in party:
            continue
        member = party_role_member(task, config)
        if not member or member in taken:
            free = [g for g in PARTY_GUESTS if g not in taken]
            member = free[0] if free else (member or PARTY_GUESTS[0])
        party[task["id"]] = {"member": member, "ts": now}
        taken.add(member)
        changed = True
    for task in tasks:
        entry = party[task["id"]]
        if task.get("status") != "running" and "done_at" not in entry:
            entry["done_at"] = now
            changed = True
    if changed:
        state["party"] = _prune(party, keep=100)
        _write_state(state)
    return {t["id"]: party[t["id"]] for t in tasks}


def render_party_row(task, entry, config, width=None, name_width=0, now=None):
    """One subagent as party chatter: who, what they're saying, HP if low, time."""
    now = time.time() if now is None else now
    rst, bld, dim = ANSI["reset"], ANSI["bold"], ANSI["dim"]
    member = entry.get("member") or "Party"
    color = ANSI.get(PARTY_COLORS.get(member, "white"), "")
    status = task.get("status")
    running = status == "running"
    knocked_out = status in ("failed", "killed")

    if running:
        glyph = f"{color}{PARTY_TWINKLE[int(now) % 2]}{rst}"
    elif status == "completed":
        glyph = f"{ANSI['green']}✓{rst}"
    elif knocked_out:
        glyph = f"{ANSI['red'] if status == 'failed' else dim}✗{rst}"
    else:
        glyph = f"{dim}∙{rst}"
    head = f"{glyph} {color}{bld}{member.ljust(name_width)}{rst}  "

    tail = []
    tokens, size = task.get("tokenCount"), task.get("contextWindowSize")
    if running and isinstance(tokens, (int, float)) and isinstance(size, (int, float)) and size > 0:
        hp = max(0.0, 100.0 - tokens / size * 100.0)
        if hp < PARTY_HP_WARN:
            tail.append(f"{ANSI['red']}{HEART_ICON} {hp:.0f}% low{rst}")
    start = task.get("startTime")
    end = now if running else entry.get("done_at")
    if isinstance(start, (int, float)) and isinstance(end, (int, float)) and not knocked_out:
        tail.append(f"{dim}{format_duration(max(0, end * 1000 - start))}{rst}")
    tail = "  ".join(tail)

    said = clean_text(task.get("label") or task.get("description") or "")
    if running and said and not said.endswith((".", "!", "?", "…")):
        said += "…"
    ko = f"{ANSI['red']}KO{rst}" + (" — " if said else "") if knocked_out else ""
    room = None
    if width is not None:
        room = width - 1 - visible_width(head + ko) - (visible_width(tail) + 2 if tail else 0) - 2
    if said:
        if room is not None:
            said = truncate(said, max(0, room)) if room >= 6 else ""
        quote_color = dim if status == "completed" else ""
        said = f'{quote_color}"{said}"{rst}' if said else ""
    body = head + ko + said
    if tail:
        gap = 2 if width is None else max(2, width - 1 - visible_width(body) - visible_width(tail))
        body += " " * gap + tail
    return body


def render_party(payload, config, now=None):
    """subagentStatusLine output: one {"id", "content"} JSON line per subagent."""
    if not config.get("party_panel", True):
        return []
    now = time.time() if now is None else now
    width = payload.get("columns")
    width = width if isinstance(width, int) and width > 0 else None
    tasks = [t for t in payload.get("tasks") or [] if isinstance(t, dict) and t.get("id")]
    if not tasks:
        return []
    party = assign_party(tasks, config, now)
    name_width = min(12, max(len(e.get("member", "")) for e in party.values()))
    return [
        json.dumps({"id": t["id"], "content": render_party_row(t, party[t["id"]], config, width, name_width, now)})
        for t in tasks
    ]


# ─── Settings Registration ───────────────────────────────────────

_KEYBLADE_COMMAND_RE = re.compile(r"keyblade\.py\b")


def _is_keyblade_command(entry):
    """True for a command that runs this script (not just any 'keyblade' wrapper)."""
    command = entry.get("command", "") if isinstance(entry, dict) else entry
    return isinstance(command, str) and bool(_KEYBLADE_COMMAND_RE.search(command))


def _read_settings(settings_path):
    """Read settings.json; {} when missing. Invalid JSON raises (never clobber it)."""
    if not os.path.exists(settings_path):
        return {}
    with open(settings_path, encoding="utf-8") as f:
        settings = json.load(f)
    if not isinstance(settings, dict):
        raise ValueError("settings.json is not a JSON object")
    return settings


def _write_settings(settings_path, settings):
    """Replace settings.json atomically: a failed write (disk full, killed)
    must never leave it truncated. Writes through a symlink to its target and
    keeps the file's permissions."""
    target = os.path.realpath(settings_path)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(target), prefix=".settings.keyblade.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
            f.write("\n")
        if os.path.exists(target):
            shutil.copymode(target, tmp)
        os.replace(tmp, target)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def register_settings(settings_path, script_path):
    """Point statusLine and subagentStatusLine at keyblade.

    Non-keyblade entries are backed up for uninstall to restore. Tweaks on an
    existing keyblade entry (padding, refreshInterval, ...) are kept.
    """
    settings = _read_settings(settings_path)
    command = f"python3 {shlex.quote(script_path)}"
    messages = []
    for key, cmd, defaults in (
        ("statusLine", command, {"padding": 0, "refreshInterval": 30}),
        ("subagentStatusLine", f"{command} --party", {}),
    ):
        existing = settings.get(key)
        entry = {"type": "command", "command": cmd}
        entry.update(defaults)
        if _is_keyblade_command(existing):
            if isinstance(existing, dict):
                entry.update({k: v for k, v in existing.items() if k not in ("type", "command")})
        elif existing:
            settings[f"_{key}_backup"] = existing
            old = existing.get("command", "") if isinstance(existing, dict) else existing
            messages.append(f"Backed up existing {key}: {old}")
        settings[key] = entry
        messages.append(f"{key} registered.")
    _write_settings(settings_path, settings)
    return messages


def unregister_settings(settings_path):
    """Remove keyblade's statusLine/subagentStatusLine, restoring any backups."""
    if not os.path.exists(settings_path):
        return []
    settings = _read_settings(settings_path)
    messages = []
    for key in ("statusLine", "subagentStatusLine"):
        backup = settings.pop(f"_{key}_backup", None)
        if _is_keyblade_command(settings.get(key)):
            if backup:
                settings[key] = backup
                messages.append(f"Restored previous {key}")
            else:
                del settings[key]
                messages.append(f"Removed {key} entry")
        elif key in settings:
            messages.append(f"{key} is not keyblade, leaving untouched")
    _write_settings(settings_path, settings)
    return messages


# ─── Preview ─────────────────────────────────────────────────────

def _preview_scenarios(work_dir, now):
    """(title, auth, payload) samples covering the HUD's states."""
    base = {
        "session_id": "keyblade-preview",
        "version": "2.1.295",
        "model": {"id": "claude-opus-5-5", "display_name": "Opus"},
        "workspace": {"current_dir": work_dir, "project_dir": work_dir, "added_dirs": []},
        "cost": {"total_cost_usd": 1.84, "total_duration_ms": 2_460_000,
                 "total_lines_added": 412, "total_lines_removed": 88},
        "context_window": {"context_window_size": 1_000_000, "remaining_percentage": 72},
        "effort": {"level": "xhigh"},
    }

    def sample(**overrides):
        data = json.loads(json.dumps(base))
        data.update(overrides)
        return data

    max_plan = {"method": "claude.ai", "provider": "firstParty", "plan": "max"}
    return [
        ("Max subscriber · PR in review · warm cache", max_plan, sample(
            session_name="statusbar refresh",
            rate_limits={"five_hour": {"used_percentage": 38, "resets_at": now + 8040},
                         "seven_day": {"used_percentage": 21, "resets_at": now + 300_000}},
            pr={"number": 12, "url": "https://github.com/emoralesb05/claude-keyblade-statusbar/pull/12",
                "review_state": "pending"},
            prompt_cache={"warm": True, "caching_observed": True, "hit_ratio": 0.91, "expires_at": now + 2520},
        )),
        ("API key · paying munny per hit", {"method": "api_key", "provider": "firstParty", "plan": None}, sample(
            cost={"total_cost_usd": 3.80, "total_duration_ms": 5_400_000,
                  "total_lines_added": 1210, "total_lines_removed": 340},
            effort={"level": "high"},
        )),
        ("Danger · MP Charge · changes requested", max_plan, sample(
            rate_limits={"five_hour": {"used_percentage": 88, "resets_at": now + 1500}},
            context_window={"context_window_size": 200_000, "remaining_percentage": 7},
            effort={"level": "max"},
            pr={"number": 12, "review_state": "changes_requested"},
        )),
        ("Anti Form · context nearly gone", max_plan, sample(
            rate_limits={"five_hour": {"used_percentage": 52, "resets_at": now + 4000}},
            context_window={"context_window_size": 200_000, "remaining_percentage": 3},
        )),
        ("Haiku on Bedrock · fast mode · no effort", {"method": None, "provider": "bedrock", "plan": None}, {
            **sample(model={"id": "claude-haiku-5-5", "display_name": "Haiku"}, fast_mode=True,
                     agent={"name": "security-reviewer"}),
            "effort": None,
        }),
    ]


def preview(args):
    """Render sample scenarios for each theme in this terminal.

    Usage: keyblade.py --preview [classic|minimal|full_rpg ...] [--width N]
    Uses your config and the current directory's git state; level-up, save
    point and party state go to a scratch directory that's removed afterwards,
    not the live state file.
    """
    global STATE_FILE
    if "--width" in args:
        idx = args.index("--width")
        if idx + 1 < len(args):
            os.environ["COLUMNS"] = args[idx + 1]
    themes = [a for a in args if a in RENDERERS] or list(RENDERERS)
    config = load_config()
    live_state = STATE_FILE
    with tempfile.TemporaryDirectory(prefix="keyblade_preview_") as scratch:
        STATE_FILE = os.path.join(scratch, "state.json")
        try:
            _render_previews(themes, config)
        finally:
            STATE_FILE = live_state


def _render_previews(themes, config):
    now = int(time.time())
    bld, dim, rst = ANSI["bold"], ANSI["dim"], ANSI["reset"]
    for theme in themes:
        print(f"\n{bld}═══ {theme} ═══{rst}")
        for title, auth, data in _preview_scenarios(os.getcwd(), now):
            print(f"{dim}── {title}{rst}")
            print(RENDERERS[theme](data, config, auth=auth))
    party = {"columns": int(os.environ.get("COLUMNS") or 0) or 100, "tasks": [
        {"id": "a1", "agentType": "Explore", "status": "running", "model": "claude-haiku-5-5",
         "tokenCount": 38_000, "contextWindowSize": 200_000, "startTime": now * 1000 - 95_000,
         "label": "Searching for statusline payload handling"},
        {"id": "a2", "name": "security-reviewer", "agentType": "general-purpose", "status": "running",
         "tokenCount": 176_000, "contextWindowSize": 200_000, "startTime": now * 1000 - 190_000,
         "label": "Auditing the auth flow"},
        {"id": "a3", "agentType": "code-reviewer", "status": "completed", "model": "claude-opus-5-5",
         "tokenCount": 640_000, "contextWindowSize": 1_000_000, "startTime": now * 1000 - 242_000,
         "label": "Reviewed keyblade.py: 2 findings"},
        {"id": "a4", "agentType": "general-purpose", "status": "failed",
         "tokenCount": 199_000, "contextWindowSize": 200_000, "startTime": now * 1000 - 300_000,
         "label": "Ran out of context"},
    ]}
    print(f"\n{bld}═══ party panel (subagentStatusLine) ═══{rst}")
    for row in render_party(party, config):
        print(json.loads(row)["content"])


# ─── Main ────────────────────────────────────────────────────────

RENDERERS = {
    "classic": render_classic,
    "minimal": render_minimal,
    "full_rpg": render_full_rpg,
}

FALLBACK = f"{ANSI['cyan']}{KEYBLADE_ICON}  Keyblade{ANSI['reset']}"


def main_party():
    """subagentStatusLine entry point. Prints nothing on error, which keeps
    Claude Code's default rows."""
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
        config = load_config()
        for row in render_party(payload, config):
            print(row)
    except Exception:
        pass


def main_settings(argv):
    """--register-settings SETTINGS [SCRIPT] / --unregister-settings SETTINGS"""
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        if argv[0] == "--register-settings":
            script = argv[2] if len(argv) > 2 else os.path.abspath(__file__)
            messages = register_settings(argv[1], script)
        else:
            messages = unregister_settings(argv[1])
    except (OSError, ValueError) as e:
        print(f"  Error: could not update {argv[1]}: {e}", file=sys.stderr)
        return 1
    for message in messages:
        print(f"  {message}")
    return 0


def _utf8_stdio():
    """Claude Code speaks UTF-8 regardless of locale. Icons must encode even
    under a non-UTF-8 locale, and lone surrogates from truncated payload
    strings print as '?' instead of raising."""
    for stream in (sys.stdin, sys.stdout):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    command = argv[0] if argv else ""
    _utf8_stdio()
    if command == "--party":
        return main_party()
    if command == "--preview":
        return preview(argv[1:])
    if command in ("--register-settings", "--unregister-settings"):
        return main_settings(argv)
    if command == "--refresh-auth" and len(argv) > 1:
        refresh_auth(argv[1], int(argv[2]) if len(argv) > 2 and argv[2].isdigit() else None)
        return 0

    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, ValueError):
        print(FALLBACK)
        return 0

    try:
        config = load_config()
        renderer = RENDERERS.get(config.get("theme", "classic"), render_classic)
        output = renderer(data, config)
    except Exception:
        output = FALLBACK
    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
