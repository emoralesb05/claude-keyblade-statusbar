#!/bin/bash
set -euo pipefail

# keyblade installer — registers Claude Code statusline and /kh skill

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
INSTALL_DIR="$BASE_DIR/hooks/keyblade"
SETTINGS="$BASE_DIR/settings.json"

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

# Detect update vs fresh install
UPDATING=false
if [ -f "$INSTALL_DIR/keyblade.py" ]; then
  UPDATING=true
  echo "  Existing install found. Updating..."
else
  echo "  May your heart be your guiding key."
fi
echo ""

# Create install directory
mkdir -p "$INSTALL_DIR"

# Symlink core files
ln -sf "$SCRIPT_DIR/keyblade.py" "$INSTALL_DIR/keyblade.py"
ln -sf "$SCRIPT_DIR/VERSION" "$INSTALL_DIR/VERSION"
ln -sf "$SCRIPT_DIR/uninstall.sh" "$INSTALL_DIR/uninstall.sh"

# Copy config only on fresh install (preserve user edits)
if [ "$UPDATING" = false ]; then
  cp "$SCRIPT_DIR/config.json" "$INSTALL_DIR/config.json"
  echo "  Created config: $INSTALL_DIR/config.json"
else
  echo "  Config preserved: $INSTALL_DIR/config.json"
fi

# Install /kh skill
SKILL_DIR="$BASE_DIR/skills/kh"
mkdir -p "$SKILL_DIR"
ln -sf "$SCRIPT_DIR/skills/kh/SKILL.md" "$SKILL_DIR/SKILL.md"
echo "  Installed /kh skill"

# Register statusLine in settings.json
echo "  Configuring statusline..."
python3 -c "
import json, os, sys

settings_path = '$SETTINGS'
install_dir = '$INSTALL_DIR'

if os.path.exists(settings_path):
    with open(settings_path) as f:
        settings = json.load(f)
else:
    settings = {}

# Check for existing statusLine and back it up
existing = settings.get('statusLine')
if existing:
    cmd = ''
    if isinstance(existing, dict):
        cmd = existing.get('command', '')
    elif isinstance(existing, str):
        cmd = existing

    if cmd and 'keyblade' not in cmd:
        settings['_statusLine_backup'] = existing
        print(f'  Backed up existing statusLine: {cmd}')

# Set keyblade statusline
settings['statusLine'] = {
    'type': 'command',
    'command': f'python3 {install_dir}/keyblade.py',
    'padding': 1
}

with open(settings_path, 'w') as f:
    json.dump(settings, f, indent=2)
    f.write('\n')

print('  StatusLine registered.')
"

# Apply theme if specified
THEME="${1:-}"
if [ -n "$THEME" ]; then
  python3 -c "
import json
config_path = '$INSTALL_DIR/config.json'
try:
    with open(config_path) as f:
        cfg = json.load(f)
except Exception:
    cfg = {}
cfg['theme'] = '$THEME'
with open(config_path, 'w') as f:
    json.dump(cfg, f, indent=2)
    f.write('\n')
print(f'  Theme set to: $THEME')
"
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
echo "    /kh  — Open the Kingdom Hearts command menu"
echo ""
echo "  The Keyblade has chosen you."
echo ""
