
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

echo " "
echo "🧠 Installing Telemoji Enhancer..."
echo "===================================="
sleep 1

# --- 1️⃣ Check system dependencies ---
echo "🔍 Checking system requirements..."

if ! command -v python3 >/dev/null 2>&1; then
    echo "📦 Installing Python3..."
    sudo apt update && sudo apt install -y python3 python3-pip
fi

# Ensure venv module is available
if ! python3 -m venv --help >/dev/null 2>&1; then
    echo "📦 Installing Python venv module..."
    sudo apt install -y python3-venv || \
    sudo apt install -y python3.12-venv || \
    sudo apt install -y python3.11-venv || \
    sudo apt install -y python3.10-venv
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

# --- 3️⃣ Create virtual environment (auto-heal) ---
if [ ! -d "$VENV_DIR" ]; then
    echo "⚙️ Creating virtual environment..."
    if ! python3 -m venv "$VENV_DIR"; then
        echo "❌ Failed to create virtual environment. Trying to fix..."
        sudo apt install -y python3-venv || \
        sudo apt install -y python3.12-venv || \
        sudo apt install -y python3.11-venv || \
        sudo apt install -y python3.10-venv
        python3 -m venv "$VENV_DIR"
    fi
else
    echo "✅ Virtual environment found."
fi

# --- 4️⃣ Activate venv and install dependencies ---
echo "📦 Installing Python dependencies..."
if [ -f "$VENV_DIR/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
else
    echo "❌ Virtual environment missing, creating again..."
    python3 -m venv "$VENV_DIR"
    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
fi
pip install --upgrade pip
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    pip install telethon
fi
deactivate

# --- 5️⃣ Ensure launcher is executable ---
if [ -f "$INSTALL_DIR/telemoji.sh" ]; then
    chmod +x "$INSTALL_DIR/telemoji.sh"
fi

# --- 6️⃣ Create launcher alias ---
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

# --- 7️⃣ Done ---
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
