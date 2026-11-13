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
from discord.ext import commands, tasks

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
        intents.voice_states = True

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

        # Start 24/7 voice keepalive loop
        if not self.voice_keepalive_loop.is_running():
            self.voice_keepalive_loop.start()

    async def ensure_voice_connection(self):
        """Ensures the bot stays connected 24/7 to the configured voice channel."""
        try:
            settings = database.get_all_settings()
            vc_id_str = settings.get("voice_channel", "0")
            if not vc_id_str or vc_id_str == "0":
                return

            vc_id = int(vc_id_str)
            target_channel = self.get_channel(vc_id)
            if not target_channel or not isinstance(target_channel, discord.VoiceChannel):
                return

            guild = target_channel.guild
            voice_client = guild.voice_client

            if voice_client is None or not voice_client.is_connected():
                print(f"[*] Connecting to 24/7 Voice Channel: {target_channel.name} ({target_channel.id})...")
                await target_channel.connect(self_deaf=True, reconnect=True)
                print(f"[+] Connected to 24/7 Voice Channel: {target_channel.name}")
            elif voice_client.channel.id != vc_id:
                print(f"[*] Moving to configured Voice Channel: {target_channel.name}...")
                await voice_client.move_to(target_channel)
        except Exception as e:
            print(f"[!] Error ensuring voice connection: {e}")

    @tasks.loop(seconds=45)
    async def voice_keepalive_loop(self):
        await self.ensure_voice_connection()

    @voice_keepalive_loop.before_loop
    async def before_voice_loop(self):
        await self.wait_until_ready()

    async def on_voice_state_update(self, member, before, after):
        # Auto-reconnect if bot is kicked/moved from voice channel
        if member.id == self.user.id and after.channel is None:
            settings = database.get_all_settings()
            vc_id_str = settings.get("voice_channel", "0")
            if vc_id_str and vc_id_str != "0":
                await asyncio.sleep(3)
                await self.ensure_voice_connection()

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

        # Connect to 24/7 voice channel
        await self.ensure_voice_connection()

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
