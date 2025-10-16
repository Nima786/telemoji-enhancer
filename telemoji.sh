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
  uninstall)
    echo "🧹 Uninstalling Telemoji Enhancer..."
    read -rp "Are you sure you want to completely remove Telemoji? (y/N): " confirm
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        sudo systemctl stop "$SERVICE_NAME" 2>/dev/null || true
        sudo systemctl disable "$SERVICE_NAME" 2>/dev/null || true
        sudo rm -f "/etc/systemd/system/$SERVICE_NAME"
        sudo systemctl daemon-reload

        # Remove alias
        sed -i '/alias telemoji=/d' "$HOME/.bashrc" 2>/dev/null || true
        sed -i '/alias telemoji=/d' "$HOME/.zshrc" 2>/dev/null || true

        # Delete app directory
        rm -rf "$INSTALL_DIR"

        # Delete sessions & logs
        find "$HOME" -maxdepth 1 -type f -name "telemoji*.session*" -delete
        find "$HOME" -maxdepth 1 -type f -name "telemoji*.log" -delete

        echo "✅ Telemoji Enhancer completely uninstalled."
        echo "You can now safely remove this script or install TelSuit."
    else
        echo "❎ Uninstall cancelled."
    fi
    ;;
  *)
    echo "📘 Usage:"
    echo "  telemoji start     → Start interactive enhancer"
    echo "  telemoji update    → Update from GitHub"
    echo "  telemoji stop      → Stop background service"
    echo "  telemoji status    → Check background service"
    echo "  telemoji reload    → Reload config & restart service"
    echo "  telemoji uninstall → Remove Telemoji completely"
    ;;
esac
