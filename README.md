🚀 Telemoji Enhancer
====================

A lightweight, multi-admin Telegram emoji enhancer that automatically converts standard emojis into **Premium Custom Emojis** — powered by **Telethon**.

* * *

⚡️ Quick Install
----------------

    curl -sSL https://raw.githubusercontent.com/Nima786/telemoji-enhancer/main/install.sh | bash
    

This one-line command installs Python, creates a virtual environment, clones the repository, and launches Telemoji Enhancer automatically.

* * *

🧠 Features
-----------

*   Multi-admin and multi-channel support
*   Automatic emoji-to-custom emoji conversion
*   Auto-starts on reboot using `systemd`
*   Simple, menu-driven configuration
*   Headless background mode for 24/7 monitoring

* * *

⚙️ Usage
--------

### ▶️ Interactive Mode (Menu)

Run manually to configure admins, channels, and emoji maps:

    telemoji start
    

This opens the interactive menu:

    1. Configure Admins
    2. Configure Channels
    3. Configure Emoji Map
    4. Start Monitoring
    5. Exit
    

### 🧩 Background Service (Automatic)

After setup, Telemoji runs automatically in the background after every reboot. It uses `systemd` to manage the process.

Check service status:

    sudo systemctl status telemoji
    

Restart manually if needed:

    sudo systemctl restart telemoji
    

* * *

🛠️ Setting up systemd Service (Manual Step)
--------------------------------------------

The installer does not yet create the background service automatically. You can set it up manually once after installation:

    sudo nano /etc/systemd/system/telemoji.service
    

Then paste the following:

    [Unit]
    Description=Telemoji Enhancer Background Service
    After=network.target
    
    [Service]
    Type=simple
    ExecStart=/root/telemoji-enhancer/venv/bin/python3 /root/telemoji-enhancer/emoji_enhancer.py --headless
    WorkingDirectory=/root/telemoji-enhancer
    Restart=always
    StandardOutput=append:/root/telemoji-enhancer/telemoji.log
    StandardError=append:/root/telemoji-enhancer/telemoji.log
    
    [Install]
    WantedBy=multi-user.target
    

Save and exit, then enable and start it:

    sudo systemctl daemon-reload
    sudo systemctl enable telemoji.service
    sudo systemctl start telemoji.service
    

Check logs:

    sudo systemctl status telemoji
    tail -n 50 ~/telemoji-enhancer/telemoji.log
    

* * *

👨‍💻 Managing Configuration
----------------------------

*   Configuration file: `~/telemoji-enhancer/enhance-emoji.ini`
*   Edit manually using `nano` or rerun the menu via `telemoji start`
*   To change which admin is used in headless mode:
    1.  Open the config file
    2.  Move your preferred admin to the top of the `"admins"` section

* * *

🔁 Updating
-----------

To update the enhancer to the latest GitHub version:

    telemoji update
    

If you’ve modified local files manually and get a merge conflict, reset safely:

    cd ~/telemoji-enhancer
    sudo systemctl stop telemoji
    git fetch --all
    git reset --hard origin/main
    chmod +x telemoji.sh
    source ~/.bashrc
    sudo systemctl daemon-reload
    sudo systemctl start telemoji
    

* * *

🧩 Optional: Background Auto-Reload
-----------------------------------

If you edit your configuration file and want to reload changes without restarting the service:

    telemoji reload
    

* * *

🧰 Manual Commands
------------------

    telemoji start   → Launch interactive menu
    telemoji update  → Update from GitHub (force sync)
    telemoji stop    → Stop the background service
    telemoji reload  → Reload configuration without restart
    

* * *

📜 Logs
-------

View live logs or troubleshoot issues:

    tail -f ~/telemoji-enhancer/telemoji.log
    

* * *

💡 Notes
--------

*   After reboot, the background service starts automatically.
*   If “Permission denied” occurs, run:
    
        chmod +x ~/telemoji-enhancer/telemoji.sh && source ~/.bashrc
    
*   To uninstall, remove the folder:
    
        rm -rf ~/telemoji-enhancer
    

* * *

📄 License
----------

This project is licensed under the **MIT License** — free to use, modify, and distribute.  
See the full license at: [MIT License](https://opensource.org/licenses/MIT)

* * *

**Repository:** [https://github.com/Nima786/telemoji-enhancer](https://github.com/Nima786/telemoji-enhancer)
