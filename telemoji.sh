#!/usr/bin/env bash
# Telemoji Enhancer Launcher

INSTALL_DIR="$HOME/telemoji-enhancer"
VENV_DIR="$INSTALL_DIR/venv"
SERVICE_NAME="telemoji.service"

echo "🚀 Starting Telemoji Enhancer..."
echo "================================"

if [ ! -d "$INSTALL_DIR" ]; then
    echo "❌ Telemoji Enhancer not installed at $INSTALL_DIR"
    exit 1
fi

cd "$INSTALL_DIR" || exit 1

case "$1" in
  start|"")
    echo "🧠 Launching the Emoji Enhancer..."
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
    python3 "$INSTALL_DIR/emoji_enhancer.py"
    deactivate
    ;;
  update)
    echo "⬆️ Updating Telemoji Enhancer..."
    git pull
    ;;
  stop)
    echo "🛑 Stopping Telemoji background service..."
    sudo systemctl stop "$SERVICE_NAME"
    echo "✅ Service stopped."
    ;;
  status)
    echo "📊 Checking Telemoji service status..."
    sudo systemctl status "$SERVICE_NAME" --no-pager -l
    ;;
  reload)
    echo "🔁 Reloading Telemoji configuration and restarting service..."
    sudo systemctl stop "$SERVICE_NAME"
    git pull
    sudo systemctl daemon-reload
    sudo systemctl start "$SERVICE_NAME"
    echo "✅ Telemoji reloaded successfully."
    ;;
  *)
    echo "📘 Usage:"
    echo "  telemoji start    → Start interactive enhancer"
    echo "  telemoji update   → Update from GitHub"
    echo "  telemoji stop     → Stop background service"
    echo "  telemoji status   → Check background service"
    echo "  telemoji reload   → Reload config & restart service"
    ;;
esac
