import sys
# Configure UTF-8 for console output on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import asyncio
import os
import discord
from discord.ext import commands

import config
import database
from views.free_panel import FreePanelView
from views.admin_panel import AdminPanelView
from server import start_server

class GlobalBypassBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True

        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
            owner_id=config.PRIMARY_OWNER_ID
        )

    async def setup_hook(self):
        # Initialize database
        database.init_db()

        # Register persistent views so buttons work across restarts
        self.add_view(FreePanelView())
        self.add_view(AdminPanelView())

        # Load Cogs
        await self.load_extension("cogs.admin_cog")

        # Sync application commands
        try:
            synced = await self.tree.sync()
            print(f"[+] Successfully synced {len(synced)} slash commands.")
        except Exception as e:
            print(f"[-] Failed to sync slash commands: {e}")

        # Start background web server for Render / monitoring
        try:
            await start_server(config.PORT)
        except Exception as e:
            print(f"[!] Web server could not bind to port {config.PORT}: {e}")

    async def on_ready(self):
        print("=" * 60)
        print(f"[*] Bot is online as: {self.user} (ID: {self.user.id})")
        print(f"[*] Guilds connected: {len(self.guilds)}")
        for g in self.guilds:
            print(f"   • {g.name} (ID: {g.id})")
        
        # Bot invite URL
        invite_url = f"https://discord.com/oauth2/authorize?client_id={self.user.id}&permissions=8&scope=bot%20applications.commands"
        print(f"[*] Bot Invite Link: {invite_url}")
        print("=" * 60)

        # Set bot presence
        activity = discord.Activity(type=discord.ActivityType.watching, name="GLOBAL BYPASS | /panel_free")
        await self.change_presence(status=discord.Status.online, activity=activity)

async def main():
    token = config.BOT_TOKEN
    if not token or token == "YOUR_BOT_TOKEN_HERE":
        print("[-] Error: No Discord bot token found in .env or config.py!")
        return

    bot = GlobalBypassBot()
    async with bot:
        await bot.start(token)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[*] Bot shut down cleanly.")
