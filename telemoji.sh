#!/usr/bin/env bash
#
# Telemoji Enhancer Launcher
# https://github.com/Nima786/telemoji-enhancer
#
# Handles start, stop, and update commands.

INSTALL_DIR="$HOME/telemoji-enhancer"
VENV_DIR="$INSTALL_DIR/venv"

echo "🚀 Starting Telemoji Enhancer..."
echo "================================"

if [ ! -d "$INSTALL_DIR" ]; then
    echo "❌ Telemoji Enhancer is not installed in $INSTALL_DIR"
    echo "Please reinstall using the installer script."
    exit 1
fi

cd "$INSTALL_DIR" || exit 1

case "$1" in
    start)
        echo "🧠 Launching the Emoji Enhancer..."
        # shellcheck disable=SC1091
        source "$VENV_DIR/bin/activate"
        python3 emoji_enhancer.py
        deactivate
        ;;
    update)
        echo "⬆️ Updating Telemoji Enhancer..."
        git pull
        ;;
    stop)
        echo "🛑 Telemoji Enhancer stopped (if it was running)."
        ;;
    *)
        echo "📘 Usage:"
        echo "  telemoji start   → Start the emoji enhancer"
        echo "  telemoji update  → Update from GitHub"
        echo "  telemoji stop    → Stop (if running)"
        ;;
esac
