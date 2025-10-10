import json
import os
import logging
import re
import asyncio
from telethon import TelegramClient, events
from telethon.tl.types import MessageEntityCustomEmoji

# --- 🎨 Colors and Config ---
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    RESET = '\033[0m'

CONFIG_FILE = 'enhance-emoji.ini'
SESSION_FILE = 'enhancer.session'
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Config Helpers ---
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)
    logger.info(f"Configuration saved to {CONFIG_FILE}")

def setup_credentials(config):
    print(f"\n{Colors.CYAN}--- Configure Credentials ---{Colors.RESET}")
    print("Press ENTER to keep the current value.")
    current_api_id = config.get('api_id', '')
    new_api_id = input(f"Enter your API ID [{current_api_id}]: ")
    config['api_id'] = new_api_id if new_api_id else current_api_id
    current_api_hash = config.get('api_hash', '')
    new_api_hash = input(f"Enter your API Hash [{current_api_hash}]: ")
    config['api_hash'] = new_api_hash if new_api_hash else current_api_hash
    current_phone = config.get('phone', '')
    new_phone = input(f"Enter your phone number [{current_phone}]: ")
    config['phone'] = new_phone if new_phone else current_phone
    current_channel = config.get('target_channel', '')
    new_channel = input(f"Enter the target channel username [{current_channel}]: ")
    config['target_channel'] = new_channel if new_channel else current_channel
    return config

def setup_emojis(config):
    if 'emoji_map' not in config:
        config['emoji_map'] = {}
    while True:
        print(f"\n{Colors.CYAN}--- Configure Emoji-to-ID Map ---{Colors.RESET}")
        print("Get Custom Emoji IDs from @RawDataBot")
        print(f"{Colors.YELLOW}1.{Colors.RESET} Add / Update an Emoji ID")
        print(f"{Colors.YELLOW}2.{Colors.RESET} Delete an Emoji ID")
        print(f"{Colors.YELLOW}3.{Colors.RESET} View Current Map")
        print(f"{Colors.YELLOW}4.{Colors.RESET} Return to Main Menu")
        choice = input("> ")
        if choice == '1':
            standard = input("Enter the standard emoji to replace: ")
            custom_id = input(f"Enter the Custom Emoji ID for '{standard}': ")
            config['emoji_map'][standard] = custom_id
            print(f"{Colors.GREEN}Map updated.{Colors.RESET}")
        elif choice == '2':
            standard = input("Enter the standard emoji to delete from the map: ")
            if standard in config['emoji_map']:
                del config['emoji_map'][standard]
                print(f"'{standard}' removed from the map.")
            else:
                print("Emoji not found in the map.")
        elif choice == '3':
            if not config['emoji_map']:
                print("\nYour emoji-to-ID map is currently empty.")
            else:
                print("\n--- Current Emoji-to-ID Map ---")
                for standard, custom_id in config['emoji_map'].items():
                    print(f"  {standard}  ->  ID: {custom_id}")
                print("-------------------------")
        elif choice == '4':
            break
        else:
            print("Invalid choice.")
    return config

# --- 🤖 Main Logic ---
async def start_monitoring(config):
    try:
        api_id, api_hash, phone = config.get('api_id'), config.get('api_hash'), config.get('phone')
        target_channel, emoji_map = config.get('target_channel'), config.get('emoji_map', {})
        if not all([api_id, api_hash, phone, target_channel]):
            logger.error("Credentials are not fully configured.")
            return

        client = TelegramClient(SESSION_FILE, int(api_id), api_hash)

        @client.on(events.NewMessage(chats=target_channel))
        async def emoji_enhancer_handler(event):
            text = event.message.text
            if not text:
                return

            # --- ✅ Step 1: Parse Markdown safely (cross-version compatible) ---
            try:
                parsed_text, parsed_entities = await client._parse_message_text(text, 'md')
            except TypeError:
                parsed_text, parsed_entities = await client._parse_message_text(text=text, parse_mode='md')

            # --- ✅ Step 2: Build emoji entities (handles multiple occurrences) ---
            matches = []
            for emoji, doc_id in emoji_map.items():
                for m in re.finditer(re.escape(emoji), parsed_text):
                    matches.append((m.start(), m.end(), emoji, int(doc_id)))

            matches.sort(key=lambda x: x[0])  # Sort by start position

            new_entities = []
            for start, end, emoji, doc_id in matches:
                prefix = parsed_text[:start]
                offset = len(prefix.encode('utf-16-le')) // 2
                length = len(emoji.encode('utf-16-le')) // 2
                new_entities.append(
                    MessageEntityCustomEmoji(offset=offset, length=length, document_id=doc_id)
                )

            if not new_entities:
                return

            # --- ✅ Step 3: Merge Markdown + custom emoji entities ---
            final_entities = (parsed_entities or []) + new_entities
            final_entities.sort(key=lambda e: e.offset)

            try:
                await event.edit(parsed_text, formatting_entities=final_entities)
                logger.info(
                    f"✅ Enhanced message {event.message.id} with {len(new_entities)} custom emoji entity(ies)"
                )
            except Exception as e:
                logger.error(f"❌ Edit failed for message {event.message.id}: {e}")

        await client.start(phone=phone)
        logger.info(f"Client started! Monitoring channel '{target_channel}' (Markdown + Emoji Safe)")
        await client.run_until_disconnected()

    except Exception as e:
        logger.critical(f"A critical error occurred: {e}")

# --- ▶️ Menu ---
async def main():
    config = load_config()
    while True:
        print(f"\n{Colors.BOLD}{Colors.GREEN}================")
        print("  Emoji Enhancer (Final Multi-Emoji + Markdown Safe)")
        print(f"================{Colors.RESET}")
        print(f"{Colors.YELLOW}1.{Colors.RESET} Configure Credentials")
        print(f"{Colors.YELLOW}2.{Colors.RESET} Configure Emoji-to-ID Map")
        print(f"{Colors.YELLOW}3.{Colors.RESET} Start Monitoring")
        print(f"{Colors.YELLOW}4.{Colors.RESET} Exit")
        print("----------------")
        choice = input("Select an option: ")
        if choice == '1':
            config = setup_credentials(config)
            save_config(config)
        elif choice == '2':
            config = setup_emojis(config)
            save_config(config)
        elif choice == '3':
            if not config.get('api_id'):
                print("\nPlease configure credentials first.")
                continue
            await start_monitoring(config)
            break
        elif choice == '4':
            print("Exiting.")
            break
        else:
            print("Invalid option.")

if __name__ == "__main__":
    asyncio.run(main())
