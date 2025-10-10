#!/usr/bin/env bash
#
# Telemoji Launcher Script
# Simplifies running Telemoji Enhancer
# https://github.com/Nima786/telemoji-enhancer

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$APP_DIR/venv"
PYTHON="$VENV_DIR/bin/python3"
SCRIPT="$APP_DIR/emoji_enhancer.py"

# Ensure virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
  echo "⚠️ Virtual environment not found. Run 'install.sh' first."
  exit 1
fi

# Activate environment
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# Handle commands
case "$1" in
  start|"")
    echo "🚀 Starting Telemoji Enhancer..."
    "$PYTHON" "$SCRIPT"
    ;;
  update)
    echo "🔄 Updating Telemoji Enhancer..."
    cd "$APP_DIR" || exit
    git pull
    pip install -r requirements.txt
    echo "✅ Update complete."
    ;;
  clean)
    echo "🧹 Cleaning cache and logs..."
    find "$APP_DIR" -name "__pycache__" -type d -exec rm -rf {} +
    rm -f "$APP_DIR"/*.log
    echo "✅ Clean complete."
    ;;
  *)
    echo "Usage: telemoji [start|update|clean]"
    ;;
esac

# Deactivate environment after running
deactivate
