class Keyblade < Formula
  desc "Kingdom Hearts themed statusline and command menu for Claude Code"
  homepage "https://github.com/emoralesb05/claude-keyblade-statusbar"
  url "https://github.com/emoralesb05/claude-keyblade-statusbar/archive/refs/tags/v1.0.0.tar.gz"
  sha256 "PLACEHOLDER_SHA256"
  license "MIT"

  depends_on "python@3"

  def install
    libexec.install "keyblade.py"
    libexec.install "config.json"
    libexec.install "VERSION"
    libexec.install "install.sh"
    libexec.install "uninstall.sh"
    (libexec/"skills/kh").install "skills/kh/SKILL.md"

    (bin/"keyblade-setup").write <<~BASH
      #!/bin/bash
      set -euo pipefail

      LIBEXEC="#{libexec}"
      BASE_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
      INSTALL_DIR="$BASE_DIR/hooks/keyblade"
      SETTINGS="$BASE_DIR/settings.json"

      # Parse args
      THEME=""
      for arg in "$@"; do
        case "$arg" in
          --theme=*) THEME="${arg#--theme=}" ;;
          --uninstall) exec bash "$LIBEXEC/uninstall.sh"; exit ;;
          --help|-h)
            echo "Usage: keyblade-setup [--theme=classic|minimal|full_rpg]"
            echo ""
            echo "Options:"
            echo "  --theme=<name>   Set initial theme (classic, minimal, full_rpg)"
            echo "  --uninstall      Remove keyblade from Claude Code"
            echo "  --help           Show this help"
            exit 0 ;;
        esac
      done

      echo ""
      echo "  ====================================="
      echo "  keyblade — Kingdom Hearts StatusLine"
      echo "  ====================================="
      echo ""

      # Verify Claude Code installed
      if [ ! -d "$BASE_DIR" ]; then
        echo "Error: $BASE_DIR not found. Is Claude Code installed?"
        exit 1
      fi
      command -v python3 &>/dev/null || { echo "Error: python3 is required"; exit 1; }

      # Detect update vs fresh
      UPDATING=false
      [ -f "$INSTALL_DIR/keyblade.py" ] && UPDATING=true

      if [ "$UPDATING" = true ]; then
        echo "  Existing install found. Updating..."
      else
        echo "  May your heart be your guiding key."
      fi
      echo ""

      # Symlink core files
      mkdir -p "$INSTALL_DIR"
      ln -sf "$LIBEXEC/keyblade.py" "$INSTALL_DIR/keyblade.py"
      ln -sf "$LIBEXEC/VERSION" "$INSTALL_DIR/VERSION"
      ln -sf "$LIBEXEC/uninstall.sh" "$INSTALL_DIR/uninstall.sh"

      # Copy config only on fresh install
      if [ "$UPDATING" = false ]; then
        cp "$LIBEXEC/config.json" "$INSTALL_DIR/config.json"
        echo "  Created config: $INSTALL_DIR/config.json"
      else
        echo "  Config preserved: $INSTALL_DIR/config.json"
      fi

      # Install /kh skill
      SKILL_DIR="$BASE_DIR/skills/kh"
      mkdir -p "$SKILL_DIR"
      ln -sf "$LIBEXEC/skills/kh/SKILL.md" "$SKILL_DIR/SKILL.md"
      echo "  Installed /kh skill"

      # Register statusLine in settings.json
      echo "  Configuring statusline..."
      python3 -c "
      import json, os

      settings_path = '$SETTINGS'
      install_dir = '$INSTALL_DIR'

      if os.path.exists(settings_path):
          with open(settings_path) as f:
              settings = json.load(f)
      else:
          settings = {}

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

      settings['statusLine'] = {
          'type': 'command',
          'command': f'python3 {install_dir}/keyblade.py',
          'padding': 1
      }

      with open(settings_path, 'w') as f:
          json.dump(settings, f, indent=2)
          f.write('\\n')

      print('  StatusLine registered.')
      "

      # Apply theme if specified
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
          f.write('\\n')
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
    BASH
  end

  def caveats
    <<~EOS
      To complete setup, run:
        keyblade-setup

      This configures the Claude Code statusline and installs the /kh skill.

      Options:
        keyblade-setup                    Install with classic theme
        keyblade-setup --theme=minimal    Use minimal theme
        keyblade-setup --theme=full_rpg   Use full RPG theme
        keyblade-setup --uninstall        Remove keyblade

      After setup, use /kh in Claude Code to open the command menu.
    EOS
  end

  test do
    input = '{"context_window":{"remaining_percentage":50,"used_percentage":50},"model":{"id":"claude-opus-4-6","display_name":"Opus"},"cost":{"total_cost_usd":0.5},"workspace":{"current_dir":"/tmp/test"}}'
    output = pipe_output("python3 #{libexec}/keyblade.py", input, 0)
    assert_match(/Ultima Weapon/, output)
  end
end
