#!/usr/bin/env bash
#
# Telemoji Enhancer Installer
# https://github.com/Nima786/telemoji-enhancer
#
# One-click setup for Python + Telethon environment
# Works on Ubuntu/Debian/most Linux distributions

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

# --- 1️⃣ System dependencies ---
echo "🔍 Checking system requirements..."

if ! command -v python3 >/dev/null 2>&1; then
    echo "📦 Installing Python3..."
    sudo apt update && sudo apt install -y python3 python3-pip
fi

# --- 2️⃣ Ensure Python venv + ensurepip available ---
echo "🔧 Ensuring Python virtual-env support..."
if ! python3 -c "import ensurepip" >/dev/null 2>&1; then
    echo "📦 Installing python3-full (includes venv + ensurepip)..."
    sudo apt update
    sudo apt install -y python3-full || sudo apt install -y python3-venv
fi

if ! command -v git >/dev/null 2>&1; then
    echo "📦 Installing Git..."
    sudo apt install -y git
fi

# --- 3️⃣ Clone / update repo ---
if [ ! -d "$INSTALL_DIR" ]; then
    echo "⬇️ Cloning Telemoji Enhancer into $INSTALL_DIR"
    git clone "$REPO_URL" "$INSTALL_DIR"
else
    echo "📁 Repo already exists — updating..."
    cd "$INSTALL_DIR"
    git pull
fi

cd "$INSTALL_DIR"

# --- 4️⃣ Create or repair venv ---
if [ -d "$VENV_DIR" ] && [ -f "$VENV_DIR/bin/activate" ]; then
    echo "✅ Valid virtual environment found."
else
    echo "⚙️ Creating new virtual environment..."
    rm -rf "$VENV_DIR"
    python3 -m venv "$VENV_DIR" || {
        echo "❌ venv creation failed — installing python3-full..."
        sudo apt install -y python3-full
        python3 -m venv "$VENV_DIR"
    }
fi

# --- 5️⃣ Install dependencies ---
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

# --- 6️⃣ Ensure launcher executable ---
if [ -f "$INSTALL_DIR/telemoji.sh" ]; then
    chmod +x "$INSTALL_DIR/telemoji.sh"
fi

# --- 7️⃣ Create alias ---
create_alias() {
    local shell_rc="$1"
    if ! grep -q "telemoji" "$shell_rc" 2>/dev/null; then
        echo "📎 Adding alias to $shell_rc"
        {
            echo ""
            echo "# Telemoji Enhancer launcher"
            echo "alias telemoji='$INSTALL_DIR/telemoji.sh'"
        } >> "$shell_rc"
    fi
}

if [[ "$SHELL" == *"bash"* ]]; then
    create_alias "$BASHRC_FILE"
elif [[ "$SHELL" == *"zsh"* ]]; then
    create_alias "$ZSHRC_FILE"
else
    create_alias "$BASHRC_FILE"
fi

# --- 8️⃣ Done ---
echo ""
echo "✅ Installation completed successfully!"
echo ""
echo "To start Telemoji Enhancer, run:"
echo ""
echo "  telemoji start"
echo ""
echo "or manually:"
echo ""
echo "  bash $INSTALL_DIR/telemoji.sh start"
echo ""
echo "🎉 Enjoy your premium emoji automation!"
echo ""
