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
import aiohttp
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

        # Start 24/7 voice keepalive loop
        if not self.voice_keepalive_loop.is_running():
            self.voice_keepalive_loop.start()

    async def ensure_voice_connection(self):
        """Ensures the bot connects to the configured voice channel without blocking the gateway."""
        if getattr(self, "_voice_connecting", False):
            return
        self._voice_connecting = True
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
                print(f"[*] Connecting to Voice Channel: {target_channel.name} ({target_channel.id})...")
                # Strict 5s timeout prevents blocking async event loop if UDP is restricted
                await asyncio.wait_for(target_channel.connect(self_deaf=True, reconnect=False), timeout=5.0)
                print(f"[+] Connected to Voice Channel: {target_channel.name}")
            elif voice_client.channel.id != vc_id:
                print(f"[*] Moving to configured Voice Channel: {target_channel.name}...")
                await asyncio.wait_for(voice_client.move_to(target_channel), timeout=5.0)
        except asyncio.TimeoutError:
            print("[!] Voice connect timed out (host environment may restrict UDP). Gateway remains unaffected.")
        except Exception as e:
            print(f"[!] Voice connection notice: {e}")
        finally:
            self._voice_connecting = False

    @tasks.loop(minutes=2)
    async def voice_keepalive_loop(self):
        await self.ensure_voice_connection()

    @voice_keepalive_loop.before_loop
    async def before_voice_loop(self):
        await self.wait_until_ready()

    async def on_voice_state_update(self, member, before, after):
        # Auto-reconnect if bot is disconnected from voice
        if member.id == self.user.id and after.channel is None:
            settings = database.get_all_settings()
            vc_id_str = settings.get("voice_channel", "0")
            if vc_id_str and vc_id_str != "0":
                await asyncio.sleep(5)
                asyncio.create_task(self.ensure_voice_connection())

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

        # Set bot presence immediately
        activity = discord.Activity(type=discord.ActivityType.watching, name="GLOBAL BYPASS | /panel_free")
        await self.change_presence(status=discord.Status.online, activity=activity)

        # Trigger voice connect in background without blocking on_ready
        asyncio.create_task(self.ensure_voice_connection())

async def main():
    token = config.BOT_TOKEN
    if not token or token == "YOUR_BOT_TOKEN_HERE":
        print("[-] Error: No Discord bot token found in .env or config.py!")
        return

    # Start Keep-Alive Web Server FIRST so Render health checks pass immediately
    try:
        await start_server(config.PORT)
    except Exception as e:
        print(f"[!] Web server binding: {e}")

    backoff = 5
    while True:
        try:
            bot = GlobalBypassBot()
            async with bot:
                print("[*] Connecting to Discord Gateway...")
                await bot.start(token)
        except (discord.HTTPException, discord.GatewayNotFound, discord.ConnectionClosed, aiohttp.ClientError) as e:
            print(f"[!] Discord connection error: {e}")
            print(f"[*] Cloudflare / rate limit hit. Automatically retrying in {backoff}s...")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60)
        except Exception as e:
            print(f"[!] Unexpected error in bot loop: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[*] Bot shut down cleanly.")
