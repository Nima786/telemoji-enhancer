#!/usr/bin/env python3
"""
Telemoji Enhancer - Main Entry Point
Author: Nima Norouzi
Repository: https://github.com/Nima786/telemoji-enhancer
"""

import sys
import platform
import logging

try:
    import telethon
    from telethon import TelegramClient
except ImportError:
    print("❌ Telethon is not installed. Run: pip install -r requirements.txt")
    sys.exit(1)

from colorama import init, Fore, Style

init(autoreset=True)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("telemoji-enhancer")


def print_header():
    """Display project header."""
    print(Fore.CYAN + Style.BRIGHT + "\n🚀 Telemoji Enhancer")
    print(Fore.WHITE + "===============================")
    print(Fore.GREEN + "A lightweight tool for auto-converting Telegram emojis "
          "to Premium Custom Emojis with Markdown support.\n")


def environment_check():
    """Check Python and Telethon versions."""
    print(Fore.YELLOW + "🔍 Environment Check:")
    print(f"  • Python version: {platform.python_version()}")
    print(f"  • Telethon version: {telethon.__version__}")
    print(f"  • Platform: {platform.system()} ({platform.machine()})\n")


def main():
    print_header()
    environment_check()
    print(Fore.CYAN + "✅ Telemoji Enhancer is installed correctly and ready to use.")
    print(Fore.WHITE + "To start the interactive enhancer menu, run:")
    print(Fore.GREEN + "  python3 emoji_enhancer.py\n")
    print(Fore.WHITE + "Next step: Add your main emoji-enhancing logic here.")
    print(Fore.MAGENTA + "Repository: https://github.com/Nima786/telemoji-enhancer")


if __name__ == "__main__":
    main()
