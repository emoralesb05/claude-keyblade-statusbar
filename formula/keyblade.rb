class Keyblade < Formula
  desc "Kingdom Hearts themed statusline and command menu for Claude Code"
  homepage "https://github.com/emoralesb05/claude-keyblade-statusbar"
  url "https://github.com/emoralesb05/claude-keyblade-statusbar/archive/refs/tags/v1.1.0.tar.gz"
  sha256 "1be9b109980b2d95b64083359e6d54898ed89644951351673bdb5d585213f8d8"
  license "MIT"

  depends_on "python@3"

  def install
    libexec.install "keyblade.py"
    libexec.install "config.json"
    libexec.install "VERSION"
    libexec.install "install.sh"
    libexec.install "uninstall.sh"
    (libexec/"skills/kh-menu").install "skills/kh-menu/SKILL.md"
    (libexec/"skills/keyblade-statusbar-config").install "skills/keyblade-statusbar-config/SKILL.md"

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

      # Install /kh-menu and /keyblade-statusbar-config skills
      for skill in kh-menu keyblade-statusbar-config; do
        mkdir -p "$BASE_DIR/skills/$skill"
        ln -sf "$LIBEXEC/skills/$skill/SKILL.md" "$BASE_DIR/skills/$skill/SKILL.md"
      done
      echo "  Installed /kh-menu and /keyblade-statusbar-config skills"

      # Register statusLine + subagentStatusLine in settings.json (backs up others)
      echo "  Configuring statusline..."
      python3 "$LIBEXEC/keyblade.py" --register-settings "$SETTINGS" "$INSTALL_DIR/keyblade.py"

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
      echo "    /kh-menu                   — Kingdom Hearts command menu"
      echo "    /keyblade-statusbar-config — Change settings"
      echo ""
      echo "  Preview every theme in this terminal:"
      echo "    python3 $INSTALL_DIR/keyblade.py --preview"
      echo ""
      echo "  The Keyblade has chosen you."
      echo ""
    BASH
  end

  def caveats
    <<~EOS
      To complete setup, run:
        keyblade-setup

      This configures the Claude Code statusline and installs the /kh-menu skill.

      Options:
        keyblade-setup                    Install with classic theme
        keyblade-setup --theme=minimal    Use minimal theme
        keyblade-setup --theme=full_rpg   Use full RPG theme
        keyblade-setup --uninstall        Remove keyblade

      After setup, use /kh-menu in Claude Code to open the command menu.
    EOS
  end

  test do
    input = '{"context_window":{"remaining_percentage":50,"used_percentage":50},"model":{"id":"claude-opus-4-6","display_name":"Opus"},"cost":{"total_cost_usd":0.5},"workspace":{"current_dir":"/tmp/test"}}'
    output = pipe_output("python3 #{libexec}/keyblade.py", input, 0)
    assert_match(/Ultima Weapon/, output)
  end
end
