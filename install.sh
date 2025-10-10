#!/usr/bin/env bash
#
# Telemoji Enhancer Installer
# https://github.com/Nima786/telemoji-enhancer
#
# One-click setup for Python + Telethon environment
# Works on Ubuntu/Debian/most Linux distributions

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# shellcheck disable=SC2129
echo "" >> "$shell_rc"

set -e  # stop on error

REPO_URL="https://github.com/Nima786/telemoji-enhancer.git"
INSTALL_DIR="$HOME/telemoji-enhancer"
VENV_DIR="$INSTALL_DIR/venv"
BASHRC_FILE="$HOME/.bashrc"
ZSHRC_FILE="$HOME/.zshrc"

echo " "
echo "🧠 Installing Telemoji Enhancer..."
echo "===================================="
sleep 1

# --- 1️⃣ Check system dependencies ---
echo "🔍 Checking system requirements..."

if ! command -v python3 >/dev/null 2>&1; then
    echo "📦 Installing Python3..."
    sudo apt update && sudo apt install -y python3 python3-venv python3-pip
fi

if ! command -v git >/dev/null 2>&1; then
    echo "📦 Installing Git..."
    sudo apt install -y git
fi

# --- 2️⃣ Clone repository ---
if [ ! -d "$INSTALL_DIR" ]; then
    echo "⬇️ Cloning Telemoji Enhancer into $INSTALL_DIR"
    git clone "$REPO_URL" "$INSTALL_DIR"
else
    echo "📁 Repo already exists — updating..."
    cd "$INSTALL_DIR"
    git pull
fi

cd "$INSTALL_DIR"

# --- 3️⃣ Create virtual environment ---
if [ ! -d "$VENV_DIR" ]; then
    echo "⚙️ Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# --- 4️⃣ Activate venv and install dependencies ---
echo "📦 Installing Python dependencies..."
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    # fallback basic dependencies
    pip install telethon
fi
deactivate

# --- 5️⃣ Create launcher alias ---
create_alias() {
    local shell_rc="$1"
    if ! grep -q "telemoji" "$shell_rc" 2>/dev/null; then
        echo "📎 Adding alias to $shell_rc"
        echo "" >> "$shell_rc"
        echo "# Telemoji Enhancer launcher" >> "$shell_rc"
        echo "alias telemoji='source $VENV_DIR/bin/activate && python3 $INSTALL_DIR/emoji_enhancer.py'" >> "$shell_rc"
        echo "deactivate" >> "$shell_rc"
    fi
}

if [ -n "$SHELL" ]; then
    if [[ "$SHELL" == *"bash"* ]]; then
        create_alias "$BASHRC_FILE"
    elif [[ "$SHELL" == *"zsh"* ]]; then
        create_alias "$ZSHRC_FILE"
    else
        create_alias "$BASHRC_FILE"
    fi
else
    create_alias "$BASHRC_FILE"
fi

# --- 6️⃣ Done ---
echo ""
echo "✅ Installation completed successfully!"
echo ""
echo "To start Telemoji Enhancer, run:"
echo ""
echo "  telemoji"
echo ""
echo "or manually:"
echo ""
echo "  source $VENV_DIR/bin/activate && python3 $INSTALL_DIR/emoji_enhancer.py"
echo ""
echo "🎉 Enjoy your premium emoji automation!"
echo ""
