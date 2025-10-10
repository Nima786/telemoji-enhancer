🚀 Telemoji Enhancer
====================

**Telemoji Enhancer** is a lightweight Python + Telethon utility that automatically converts normal emojis into **Telegram Premium custom emojis** inside your channel posts — while keeping **Markdown formatting** intact and supporting multiple channels and admin accounts.

* * *

⚡ Quick Install
---------------

Copy and paste this command into your terminal to install everything automatically:

    curl -sSL https://raw.githubusercontent.com/Nima786/telemoji-enhancer/main/install.sh | bash

* * *

✨ Features
----------

*   ✅ Converts standard emojis into Premium custom emojis automatically
*   ✅ Preserves Markdown (`**bold**`, `_italic_`, `[links](url)`, etc.)
*   ✅ Supports multiple channels and multiple admins
*   ✅ Interactive menu for easy setup and configuration
*   ✅ One-click shell installer for any Linux server
*   ✅ Works smoothly on Ubuntu, Debian, and similar distributions

* * *

📦 Installation Details
-----------------------

The one-click installer will:

1.  Install Python 3 and Git (if missing)
2.  Clone this repository
3.  Create a Python virtual environment
4.  Install dependencies
5.  Create a `telemoji` command alias for quick start

**Manual Installation (Optional):**

git clone https://github.com/Nima786/telemoji-enhancer.git
cd telemoji-enhancer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 emoji\_enhancer.py

* * *

⚙️ Usage
--------

Start the interactive menu:

    telemoji start

Or run manually:

    python3 emoji_enhancer.py

* * *

🪄 Configuration
----------------

All configuration is saved automatically in `enhance-emoji.ini` after first run.

*   Admin credentials (API ID, API hash, phone number)
*   List of monitored Telegram channels
*   Emoji → Custom ID mapping

You can manage everything through the built-in interactive menu.

* * *

🧑‍💻 Requirements
------------------

*   Python 3.9 or newer
*   Telethon 1.33 or newer
*   A Telegram Premium account (required to apply custom emojis)

* * *

📜 License
----------

This project is licensed under the [MIT License](https://github.com/Nima786/telemoji-enhancer/blob/main/LICENSE).

* * *

💡 Credits
----------

Developed by [Nima Norouzi](https://github.com/Nima786)  
Inspired by the Telegram community ❤️
