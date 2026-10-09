#!/bin/bash
set -euo pipefail

# keyblade installer — registers Claude Code statusline and /kh-menu skill
# Supports two modes:
#   Local:  bash install.sh [theme]        (run from cloned repo)
#   Remote: bash <(curl -fsSL URL) [theme] (downloads files from GitHub)

REPO="emoralesb05/claude-keyblade-statusbar"
BRANCH="main"
RAW_URL="https://raw.githubusercontent.com/$REPO/$BRANCH"

BASE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
INSTALL_DIR="$BASE_DIR/hooks/keyblade"
SETTINGS="$BASE_DIR/settings.json"

# Detect local vs remote mode
LOCAL_MODE=false
if [ -n "${BASH_SOURCE[0]:-}" ] && [ "${BASH_SOURCE[0]}" != "bash" ] && [ -f "${BASH_SOURCE[0]}" ]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  if [ -f "$SCRIPT_DIR/keyblade.py" ]; then
    LOCAL_MODE=true
  fi
fi

THEME="${1:-}"
case "$THEME" in
  ""|classic|minimal|full_rpg) ;;
  *) echo "Error: unknown theme '$THEME' (use classic, minimal, or full_rpg)"; exit 1 ;;
esac

echo ""
echo "  ====================================="
echo "  keyblade — Kingdom Hearts StatusLine"
echo "  ====================================="
echo ""

# Verify prerequisites
if [ ! -d "$BASE_DIR" ]; then
  echo "Error: $BASE_DIR not found. Is Claude Code installed?"
  exit 1
fi

if ! command -v python3 &>/dev/null; then
  echo "Error: python3 is required"
  exit 1
fi

# Detect update vs fresh install. The config is what must survive an update,
# so key off it (a dangling symlink to keyblade.py would read as "fresh").
HAS_CONFIG=false
[ -f "$INSTALL_DIR/config.json" ] && HAS_CONFIG=true
if [ -e "$INSTALL_DIR/keyblade.py" ] || [ "$HAS_CONFIG" = true ]; then
  echo "  Existing install found. Updating..."
else
  echo "  May your heart be your guiding key."
fi
echo ""

# Create install directory
mkdir -p "$INSTALL_DIR"
mkdir -p "$BASE_DIR/skills/kh-menu"
mkdir -p "$BASE_DIR/skills/keyblade-statusbar-config"

# --- Install files ---

# Remove the destination first: a Homebrew setup leaves symlinks into the
# Cellar here, and cp/curl would write through them (or fail if dangling).
install_file() {
  local src="$1"
  local dest="$2"
  rm -f "$dest"
  if [ "$LOCAL_MODE" = true ]; then
    cp "$SCRIPT_DIR/$src" "$dest"
  else
    echo "  Downloading $(basename "$dest")..."
    curl -fsSL "$RAW_URL/$src" -o "$dest"
  fi
}

if [ "$LOCAL_MODE" = true ]; then
  echo "  Installing from local source..."
else
  echo "  Installing from GitHub..."
fi
install_file keyblade.py "$INSTALL_DIR/keyblade.py"
install_file VERSION "$INSTALL_DIR/VERSION"
install_file uninstall.sh "$INSTALL_DIR/uninstall.sh"
install_file skills/kh-menu/SKILL.md "$BASE_DIR/skills/kh-menu/SKILL.md"
install_file skills/keyblade-statusbar-config/SKILL.md "$BASE_DIR/skills/keyblade-statusbar-config/SKILL.md"

if [ "$HAS_CONFIG" = false ]; then
  install_file config.json "$INSTALL_DIR/config.json"
  echo "  Created config: $INSTALL_DIR/config.json"
else
  echo "  Config preserved: $INSTALL_DIR/config.json"
fi

chmod +x "$INSTALL_DIR/keyblade.py" "$INSTALL_DIR/uninstall.sh"

echo "  Installed /kh-menu and /keyblade-statusbar-config skills"

# Register statusLine + subagentStatusLine in settings.json (backs up others)
echo "  Configuring statusline..."
python3 "$INSTALL_DIR/keyblade.py" --register-settings "$SETTINGS"

# Apply theme if specified (validated above; passed as argv, not spliced into code)
if [ -n "$THEME" ]; then
  python3 - "$INSTALL_DIR/config.json" "$THEME" <<'PY'
import json, sys
config_path, theme = sys.argv[1], sys.argv[2]
try:
    with open(config_path) as f:
        cfg = json.load(f)
except Exception:
    cfg = {}
cfg['theme'] = theme
with open(config_path, 'w') as f:
    json.dump(cfg, f, indent=2)
    f.write('\n')
print(f'  Theme set to: {theme}')
PY
fi

echo ""
echo "  ====================================="
echo "  Setup complete!"
echo "  ====================================="
echo ""
echo "  Config: $INSTALL_DIR/config.json"
echo "  Themes: classic (default), minimal, full_rpg"
echo ""
echo "  Commands:"
echo "    /kh-menu                   — Kingdom Hearts command menu"
echo "    /keyblade-statusbar-config — Change settings"
echo ""
echo "  Preview every theme in this terminal:"
echo "    python3 $INSTALL_DIR/keyblade.py --preview"
echo ""
echo "  The Keyblade has chosen you."
echo ""
