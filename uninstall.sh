#!/bin/bash
set -euo pipefail

# keyblade uninstaller — removes statusline and restores previous config

BASE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
INSTALL_DIR="$BASE_DIR/hooks/keyblade"
SETTINGS="$BASE_DIR/settings.json"

echo ""
echo "  === keyblade uninstaller ==="
echo ""

# Remove statusLine + subagentStatusLine from settings.json, restoring backups.
# Prefer the keyblade.py next to this script (Homebrew runs it from libexec).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KEYBLADE_PY="$SCRIPT_DIR/keyblade.py"
[ -f "$KEYBLADE_PY" ] || KEYBLADE_PY="$INSTALL_DIR/keyblade.py"

if [ -f "$SETTINGS" ] && [ -f "$KEYBLADE_PY" ]; then
  python3 "$KEYBLADE_PY" --unregister-settings "$SETTINGS"
fi

# Remove skills
for skill in kh-menu keyblade-statusbar-config; do
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
