import json
import os
import logging
import re
import asyncio
import sys
from telethon import TelegramClient, events
from telethon.tl.types import MessageEntityCustomEmoji


# --- 🎨 Colors and Logging Setup ---
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    RESET = '\033[0m'


CONFIG_FILE = 'enhance-emoji.ini'

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# --- ⚙️ Config Management ---
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            try:
                cfg = json.load(f)
            except json.JSONDecodeError:
                cfg = {}
    else:
        cfg = {}

    cfg.setdefault("admins", {})
    cfg.setdefault("channels", [])
    cfg.setdefault("emoji_map", {})
    return cfg


def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)
    logger.info(f"Configuration saved to {CONFIG_FILE}")


# --- 🧑‍💻 Admin Management ---
def setup_admins(config):
    while True:
        print(f"\n{Colors.CYAN}--- Configure Admin Accounts ---{Colors.RESET}")
        print(f"{Colors.YELLOW}1.{Colors.RESET} Add / Update Admin")
        print(f"{Colors.YELLOW}2.{Colors.RESET} Delete Admin")
        print(f"{Colors.YELLOW}3.{Colors.RESET} View Admins")
        print(f"{Colors.YELLOW}4.{Colors.RESET} Return to Main Menu")
        choice = input("> ")

        if choice == '1':
            phone = input("Enter admin phone number (e.g. +1234567890): ").strip()
            api_id = input("Enter API ID: ").strip()
            api_hash = input("Enter API Hash: ").strip()
            config["admins"][phone] = {"api_id": api_id, "api_hash": api_hash}
            print(f"{Colors.GREEN}Admin {phone} added/updated.{Colors.RESET}")

        elif choice == '2':
            if not config["admins"]:
                print("No admins to delete.")
                continue
            print("\n--- Current Admins ---")
            for i, phone in enumerate(config["admins"], start=1):
                print(f"{i}. {phone}")
            idx = input("Select admin number to delete: ")
            if idx.isdigit() and 1 <= int(idx) <= len(config["admins"]):
                phone = list(config["admins"].keys())[int(idx) - 1]
                del config["admins"][phone]
                print(f"Removed admin {phone}")
            else:
                print("Invalid selection.")

        elif choice == '3':
            if not config["admins"]:
                print("No admins configured.")
            else:
                print("\n--- Configured Admins ---")
                for phone, creds in config["admins"].items():
                    print(
                        f"{phone} → ID:{creds['api_id']}, "
                        f"HASH:{creds['api_hash'][:6]}****"
                    )

        elif choice == '4':
            break
        else:
            print("Invalid option.")
    return config


# --- 📢 Channel Management ---
def setup_channels(config):
    while True:
        print(f"\n{Colors.CYAN}--- Configure Channels ---{Colors.RESET}")
        print(f"{Colors.YELLOW}1.{Colors.RESET} Add Channel")
        print(f"{Colors.YELLOW}2.{Colors.RESET} Remove Channel")
        print(f"{Colors.YELLOW}3.{Colors.RESET} View Channels")
        print(f"{Colors.YELLOW}4.{Colors.RESET} Return to Main Menu")
        choice = input("> ")

        if choice == '1':
            ch = input("Enter target channel username (e.g. @mychannel): ").strip()
            if ch and ch not in config["channels"]:
                config["channels"].append(ch)
                print(f"{Colors.GREEN}Added {ch}{Colors.RESET}")
            else:
                print("Already exists or invalid.")

        elif choice == '2':
            if not config["channels"]:
                print("No channels added yet.")
                continue
            print("\n--- Current Channels ---")
            for i, ch in enumerate(config["channels"], start=1):
                print(f"{i}. {ch}")
            idx = input("Select channel number to remove: ")
            if idx.isdigit() and 1 <= int(idx) <= len(config["channels"]):
                removed = config["channels"].pop(int(idx) - 1)
                print(f"Removed {removed}")
            else:
                print("Invalid selection.")

        elif choice == '3':
            if not config["channels"]:
                print("No channels configured.")
            else:
                print("\n--- Configured Channels ---")
                for i, ch in enumerate(config["channels"], start=1):
                    print(f"{i}. {ch}")

        elif choice == '4':
            break
        else:
            print("Invalid choice.")
    return config


# --- 😀 Emoji Map Management ---
def setup_emojis(config):
    if 'emoji_map' not in config:
        config['emoji_map'] = {}

    while True:
        print(f"\n{Colors.CYAN}--- Configure Emoji-to-ID Map ---{Colors.RESET}")
        print("Get Custom Emoji IDs from @RawDataBot")
        print(f"{Colors.YELLOW}1.{Colors.RESET} Add / Update Emoji ID")
        print(f"{Colors.YELLOW}2.{Colors.RESET} Delete Emoji ID")
        print(f"{Colors.YELLOW}3.{Colors.RESET} View Current Map")
        print(f"{Colors.YELLOW}4.{Colors.RESET} Return to Main Menu")
        choice = input("> ")

        if choice == '1':
            standard = input("Enter standard emoji: ").strip()
            custom_id = input(f"Enter Custom Emoji ID for '{standard}': ").strip()
            config['emoji_map'][standard] = custom_id
            print(f"{Colors.GREEN}Map updated.{Colors.RESET}")

        elif choice == '2':
            if not config['emoji_map']:
                print("Map is empty.")
                continue
            print("\n--- Current Emoji Map ---")
            for i, (standard, cid) in enumerate(config['emoji_map'].items(), start=1):
                print(f"{i}. {standard} → ID: {cid}")
            idx = input("Select number to delete: ")
            if idx.isdigit() and 1 <= int(idx) <= len(config['emoji_map']):
                key = list(config['emoji_map'].keys())[int(idx) - 1]
                del config['emoji_map'][key]
                print(f"Deleted '{key}' from map.")
            else:
                print("Invalid selection.")

        elif choice == '3':
            if not config['emoji_map']:
                print("Map is empty.")
            else:
                print("\n--- Current Emoji Map ---")
                for i, (standard, cid) in enumerate(
                    config['emoji_map'].items(), start=1
                ):
                    print(f"{i}. {standard} → ID: {cid}")

        elif choice == '4':
            break
        else:
            print("Invalid choice.")
    return config


# --- 🤖 Main Telethon Logic ---
async def start_monitoring(config, auto=False):
    if not config["admins"]:
        print("⚠️ No admins configured.")
        return

    if not config["channels"]:
        print("⚠️ No channels configured.")
        return

    admins = list(config["admins"].keys())
    if auto:
        selected_admin = admins[0]
        print(f"🤖 Auto-selected admin: {selected_admin}")
    else:
        print("\n--- Available Admins ---")
        for i, phone in enumerate(admins, start=1):
            print(f"{i}. {phone}")
        sel = input("Select which admin to use: ")
        if not sel.isdigit() or int(sel) < 1 or int(sel) > len(admins):
            print("Invalid selection.")
            return
        selected_admin = admins[int(sel) - 1]

    creds = config["admins"][selected_admin]
    api_id, api_hash, phone = creds["api_id"], creds["api_hash"], selected_admin
    client = TelegramClient(f"enhancer_{phone}.session", int(api_id), api_hash)

            # --- Rate limit setup ---
           WINDOW_SECONDS   = 2  # dedupe window seconds
            processing_lock = asyncio.Lock()
            last_processed = {}
        
            async def handler(event):
                async with processing_lock:
                            key = (event.chat_id, event.message.id)
                now = asyncio.get_event_loop().time()
                if key in last_processed and now - last_processed[key] < WINDOW_SECONDS:
                    return
                last_processed[key] = now

            text = event.message.text
            if not text:
                return

                    parsed_text = text
                        parsed_entities = event.message.entities or []

            matches = []
            for emoji, doc_id in config['emoji_map'].items():
                for m in re.finditer(re.escape(emoji), parsed_text):
                    matches.append((m.start(), m.end(), emoji, int(doc_id)))

            matches.sort(key=lambda x: x[0])
            new_entities = []

            for start, end, emoji, doc_id in matches:
                prefix = parsed_text[:start]
                offset = len(prefix.encode('utf-16-le')) // 2
                length = len(emoji.encode('utf-16-le')) // 2
                new_entities.append(
                    MessageEntityCustomEmoji(
                        offset=offset, length=length, document_id=doc_id
                    )
                )

            if not new_entities:
                return

            final_entities = (parsed_entities or []) + new_entities
            final_entities.sort(key=lambda e: e.offset)

            try:
                await event.edit(parsed_text, formatting_entities=final_entities)
                logger.info(
                    f"✅ Enhanced message {event.message.id} in {event.chat.username}"
                )
            except Exception as e:
                logger.error(f"❌ Failed editing message {event.message.id}: {e}")

    for ch in config["channels"]:
        client.add_event_handler(handler, events.NewMessage(chats=ch))
        client.add_event_handler(handler, events.MessageEdited(chats=ch))
        logger.info(f"Monitoring channel: {ch}")

    await client.start(phone=phone)
    logger.info(f"Client started under admin {phone}")
    await client.run_until_disconnected()


# --- ▶️ Main Menu ---
async def main():
    config = load_config()

    while True:
        print(f"\n{Colors.BOLD}{Colors.GREEN}=============================")
        print(" Emoji Enhancer Pro (Multi-Admin + Multi-Channel)")
        print(f"============================={Colors.RESET}")
        print(f"{Colors.YELLOW}1.{Colors.RESET} Configure Admins")
        print(f"{Colors.YELLOW}2.{Colors.RESET} Configure Channels")
        print(f"{Colors.YELLOW}3.{Colors.RESET} Configure Emoji Map")
        print(f"{Colors.YELLOW}4.{Colors.RESET} Start Monitoring")
        print(f"{Colors.YELLOW}5.{Colors.RESET} Exit")
        print("----------------")
        choice = input("Select an option: ")

        if choice == '1':
            config = setup_admins(config)
            save_config(config)
        elif choice == '2':
            config = setup_channels(config)
            save_config(config)
        elif choice == '3':
            config = setup_emojis(config)
            save_config(config)
        elif choice == '4':
            await start_monitoring(config)
            break
        elif choice == '5':
            print("Exiting.")
            break
        else:
            print("Invalid option.")


async def auto_start():
    """Run monitoring directly without showing the menu."""
    config = load_config()
    await start_monitoring(config, auto=True)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--headless":
        asyncio.run(auto_start())
    else:
        asyncio.run(main())
