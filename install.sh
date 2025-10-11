#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telemoji Enhancer
Convert standard emojis in Telegram posts into premium custom emojis,
with Markdown safety, multi-channel support, and multi-admin selection.
"""

import asyncio
import configparser
import logging
import os
import re
from telethon import TelegramClient, events
from telethon.tl.types import MessageEntityCustomEmoji
from telethon.errors import MessageNotModifiedError


CONFIG_FILE = "emoji_enhancer.ini"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
log = logging.getLogger(__name__)

# ------------------------- #
# Emoji Conversion Map
# ------------------------- #

DEFAULT_EMOJI_MAP = {
    "😎": 5436022382600000000,
    "🔥": 5436022382600000001,
    "❤️": 5436022382600000002,
    "👍": 5436022382600000003,
    "💪": 5436022382600000004,
}

# ------------------------- #
# Config Manager
# ------------------------- #


def load_config():
    cfg = configparser.ConfigParser()
    if not os.path.exists(CONFIG_FILE):
        cfg["ADMINS"] = {}
        cfg["CHANNELS"] = {}
        cfg["EMOJIS"] = {k: str(v) for k, v in DEFAULT_EMOJI_MAP.items()}
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            cfg.write(f)
    else:
        cfg.read(CONFIG_FILE, encoding="utf-8")
    return cfg


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        cfg.write(f)

# ------------------------- #
# Emoji Enhancer
# ------------------------- #


async def enhance_message(client, event, emoji_map):
    """Replace normal emojis with premium ones, keeping Markdown intact."""
    try:
        original_text = event.message.text or ""
        if not original_text:
            return

        new_entities = event.message.entities or []
        new_text = original_text

        # Replace all occurrences of each emoji
        for emoji, _ in emoji_map.items():
            new_text = re.sub(re.escape(emoji), emoji, new_text)

        # Skip if unchanged
        if new_text == original_text:
            return

        # Build custom emoji entities
        updated_entities = []
        for match in re.finditer("|".join(map(re.escape, emoji_map.keys())), new_text):
            emoji_char = match.group(0)
            custom_id = int(emoji_map[emoji_char])
            updated_entities.append(
                MessageEntityCustomEmoji(
                    offset=match.start(),
                    length=len(emoji_char),
                    document_id=custom_id,
                )
            )

        # Merge Markdown entities
        if new_entities:
            updated_entities.extend(new_entities)

        await client.edit_message(
            event.message.peer_id,
            event.message.id,
            new_text,
            formatting_entities=updated_entities,
        )

        log.info("✅ Enhanced message %s in %s", event.message.id, event.chat.title)

    except MessageNotModifiedError:
        log.warning("⚠️ Message %s unchanged (not modified).", event.message.id)
    except Exception as e:
        log.error("❌ Failed to enhance message %s: %s", event.message.id, e)

# ------------------------- #
# Telethon Client Setup
# ------------------------- #


async def start_monitor(admin_name, api_id, api_hash, phone, channels):
    client = TelegramClient(admin_name, api_id, api_hash)

    @client.on(events.NewMessage(chats=channels))
    async def handler(event):
        cfg = load_config()
        emoji_map = {k: int(v) for k, v in cfg["EMOJIS"].items()}
        await enhance_message(client, event, emoji_map)

    await client.start(phone=phone)
    log.info("Client started for admin '%s' monitoring: %s", admin_name, channels)
    await client.run_until_disconnected()

# ------------------------- #
# Interactive Menu
# ------------------------- #


def main_menu():
    cfg = load_config()

    while True:
        print("\n🚀 Telemoji Enhancer Main Menu")
        print("================================")
        print("1️⃣  Add Admin Account")
        print("2️⃣  Add Channel to Monitor")
        print("3️⃣  View/Edit Emoji Map")
        print("4️⃣  Start Monitoring")
        print("5️⃣  Exit")

        choice = input("\nSelect option: ").strip()

        if choice == "1":
            add_admin(cfg)
        elif choice == "2":
            add_channel(cfg)
        elif choice == "3":
            manage_emoji_map(cfg)
        elif choice == "4":
            start_enhancer(cfg)
        elif choice == "5":
            print("👋 Exiting Telemoji Enhancer.")
            break
        else:
            print("❌ Invalid choice.")


def add_admin(cfg):
    name = input("Admin name (unique): ").strip()
    if not name:
        print("❌ Invalid name.")
        return
    api_id = input("API ID: ").strip()
    api_hash = input("API Hash: ").strip()
    phone = input("Phone number (+countrycode): ").strip()
    cfg["ADMINS"][name] = f"{api_id}:{api_hash}:{phone}"
    save_config(cfg)
    print(f"✅ Admin '{name}' added.")


def add_channel(cfg):
    channel = input("Channel username (e.g., @mychannel): ").strip()
    if not channel:
        print("❌ Invalid channel.")
        return
    cfg["CHANNELS"][channel] = "True"
    save_config(cfg)
    print(f"✅ Channel '{channel}' added for monitoring.")


def manage_emoji_map(cfg):
    emojis = cfg["EMOJIS"]
    print("\n🔤 Current Emoji → Custom ID Map:")
    for i, (emoji, eid) in enumerate(emojis.items(), start=1):
        print(f"  {i}. {emoji} → {eid}")

    print("\n1️⃣  Add new emoji")
    print("2️⃣  Edit existing")
    print("3️⃣  Delete")
    print("4️⃣  Back")
    sub = input("Choose: ").strip()

    if sub == "1":
        emoji = input("Emoji: ").strip()
        eid = input("Custom Emoji ID: ").strip()
        emojis[emoji] = eid
    elif sub == "2":
        emoji = input("Emoji to edit: ").strip()
        if emoji in emojis:
            emojis[emoji] = input("New Custom Emoji ID: ").strip()
    elif sub == "3":
        emoji = input("Emoji to delete: ").strip()
        emojis.pop(emoji, None)

    save_config(cfg)
    print("✅ Emoji map updated.")


def start_enhancer(cfg):
    if not cfg["ADMINS"]:
        print("⚠️ No admins configured.")
        return
    if not cfg["CHANNELS"]:
        print("⚠️ No channels configured.")
        return

    print("\n👥 Available Admins:")
    admins = list(cfg["ADMINS"].keys())
    for i, name in enumerate(admins, start=1):
        print(f"  {i}. {name}")
    idx = input("Select admin: ").strip()

    try:
        admin_name = admins[int(idx) - 1]
    except (IndexError, ValueError):
        print("❌ Invalid choice.")
        return

    api_id, api_hash, phone = cfg["ADMINS"][admin_name].split(":")
    channels = list(cfg["CHANNELS"].keys())

    print(f"\n📡 Starting monitor for {admin_name} on {len(channels)} channel(s)...")
    asyncio.run(start_monitor(admin_name, api_id, api_hash, phone, channels))

# ------------------------- #
# Entry Point
# ------------------------- #


if __name__ == "__main__":
    main_menu()
