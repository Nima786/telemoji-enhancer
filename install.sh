#!/usr/bin/env bash
#
# Telemoji Enhancer Installer
# https://github.com/Nima786/telemoji-enhancer
#
# One-click setup for Python + Telethon environment
# Auto-launches safely if interactive

set -e  # stop on error

REPO_URL="https://github.com/Nima786/telemoji-enhancer.git"
INSTALL_DIR="$HOME/telemoji-enhancer"
VENV_DIR="$INSTALL_DIR/venv"
BASHRC_FILE="$HOME/.bashrc"
ZSHRC_FILE="$HOME/.zshrc"

echo ""
echo "🧠 Installing Telemoji Enhancer..."
echo "===================================="
sleep 1

# --- 1️⃣ Check dependencies ---
echo "🔍 Checking system requirements..."

if ! command -v python3 >/dev/null 2>&1; then
    echo "📦 Installing Python3..."
    sudo apt update && sudo apt install -y python3 python3-pip
fi

echo "🔧 Ensuring Python venv support..."
if ! python3 -c "import ensurepip" >/dev/null 2>&1; then
    echo "📦 Installing python3-full (includes venv + ensurepip)..."
    sudo apt update
    sudo apt install -y python3-full || sudo apt install -y python3-venv
fi

if ! command -v git >/dev/null 2>&1; then
    echo "📦 Installing Git..."
    sudo apt install -y git
fi

# --- 2️⃣ Clone or update repo ---
if [ ! -d "$INSTALL_DIR" ]; then
    echo "⬇️ Cloning Telemoji Enhancer into $INSTALL_DIR"
    git clone "$REPO_URL" "$INSTALL_DIR"
else
    echo "📁 Repo already exists — updating..."
    cd "$INSTALL_DIR"
    git pull
fi

cd "$INSTALL_DIR"

# --- 3️⃣ Create or repair venv ---
if [ ! -f "$VENV_DIR/bin/activate" ]; then
    echo "⚙️ Creating new virtual environment..."
    rm -rf "$VENV_DIR"
    python3 -m venv "$VENV_DIR" || {
        echo "❌ venv creation failed — installing python3-full..."
        sudo apt install -y python3-full
        python3 -m venv "$VENV_DIR"
    }
else
    echo "✅ Virtual environment found."
fi

# --- 4️⃣ Install dependencies ---
echo "📦 Installing Python dependencies..."
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    pip install telethon
fi
deactivate

# --- 5️⃣ Auto-generate launcher ---
echo "⚙️ Generating Telemoji launcher..."
cat > "$INSTALL_DIR/telemoji.sh" <<'EOF'
#!/usr/bin/env bash
# Telemoji Enhancer Launcher

INSTALL_DIR="$HOME/telemoji-enhancer"
VENV_DIR="$INSTALL_DIR/venv"

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
    echo "🛑 Telemoji Enhancer stopped (if running)."
    ;;
  *)
    echo "📘 Usage:"
    echo "  telemoji start   → Start the emoji enhancer"
    echo "  telemoji update  → Update from GitHub"
    echo "  telemoji stop    → Stop (if running)"
    ;;
esac
EOF

chmod +x "$INSTALL_DIR/telemoji.sh"

# --- 6️⃣ Create alias ---
create_alias() {
    local shell_rc="$1"
    if ! grep -q "telemoji=" "$shell_rc" 2>/dev/null; then
        echo "📎 Adding alias to $shell_rc"
        {
            echo ""
            echo "# Telemoji Enhancer launcher"
            echo "alias telemoji='$INSTALL_DIR/telemoji.sh'"
        } >> "$shell_rc"
    fi
    alias telemoji="$INSTALL_DIR/telemoji.sh"
}

if [[ "$SHELL" == *"bash"* ]]; then
    create_alias "$BASHRC_FILE"
elif [[ "$SHELL" == *"zsh"* ]]; then
    create_alias "$ZSHRC_FILE"
else
    create_alias "$BASHRC_FILE"
fi

# --- 7️⃣ Done (safe auto-launch if interactive) ---
echo ""
echo "✅ Installation completed successfully!"
echo ""

if [ -t 0 ]; then
    echo "🎉 Launching Telemoji Enhancer now..."
    echo ""
    bash "$INSTALL_DIR/telemoji.sh" start
else
    echo "💡 Non-interactive shell detected."
    echo "To start Telemoji Enhancer, run:"
    echo "  telemoji start"
    echo ""
fi

echo "🎉 Enjoy your premium emoji automation!"
echo ""
