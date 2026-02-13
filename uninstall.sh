#!/bin/bash
set -euo pipefail

# keyblade uninstaller — removes statusline and restores previous config

BASE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
INSTALL_DIR="$BASE_DIR/hooks/keyblade"
SETTINGS="$BASE_DIR/settings.json"

echo ""
echo "  === keyblade uninstaller ==="
echo ""

# Restore statusLine backup in settings.json
if [ -f "$SETTINGS" ]; then
  python3 -c "
import json, os

settings_path = '$SETTINGS'
with open(settings_path) as f:
    settings = json.load(f)

sl = settings.get('statusLine', {})
is_keyblade = False
if isinstance(sl, dict):
    is_keyblade = 'keyblade' in sl.get('command', '')

if is_keyblade:
    backup = settings.pop('_statusLine_backup', None)
    if backup:
        settings['statusLine'] = backup
        print('  Restored previous statusLine')
    else:
        del settings['statusLine']
        print('  Removed statusLine entry')
else:
    print('  StatusLine is not keyblade, leaving untouched')

settings.pop('_statusLine_backup', None)

with open(settings_path, 'w') as f:
    json.dump(settings, f, indent=2)
    f.write('\n')
"
fi

# Remove skills
for skill in kh keyblade-statusbar-config; do
  SKILL_DIR="$BASE_DIR/skills/$skill"
  if [ -d "$SKILL_DIR" ]; then
    rm -rf "$SKILL_DIR"
    echo "  Removed /$skill skill"
  fi
done

# Remove install directory
if [ -d "$INSTALL_DIR" ]; then
  rm -rf "$INSTALL_DIR"
  echo "  Removed $INSTALL_DIR"
fi

echo ""
echo "  === Uninstall complete ==="
echo "  May your heart be your guiding key."
echo ""
