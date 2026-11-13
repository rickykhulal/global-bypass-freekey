import discord
from discord.ui import View, Button
import datetime
import time
import database
import config

# In-memory cooldown dictionary: {user_id: last_click_timestamp}
COOLDOWNS = {}
COOLDOWN_SECONDS = 5

def parse_hex_color(hex_str: str, default: int = 0x00FFA2) -> int:
    try:
        clean = hex_str.strip().replace("#", "")
        return int(clean, 16)
    except Exception:
        return default

def check_user_role_access(interaction: discord.Interaction) -> tuple[bool, str]:
    """
    Checks if the interacting user has the required role to use the bot.
    Returns: (is_allowed: bool, required_roles_display: str)
    """
    user = interaction.user

    # 0. Primary Bot Owner always bypasses all restrictions
    if user.id == config.PRIMARY_OWNER_ID or user.id in config.DEFAULT_ADMIN_IDS:
        return True, ""

    # 1. Guild Administrators always bypass
    if hasattr(user, "guild_permissions") and user.guild_permissions.administrator:
        return True, ""

    settings = database.get_all_settings()

    # 2. Admin panel owners always bypass
    owners_str = settings.get("admin_panel_owners", "")
    owner_ids = [int(i.strip()) for i in owners_str.split(",") if i.strip().isdigit()]
    if user.id in owner_ids:
        return True, ""

    # 3. Check allowed FREE roles
    allowed_roles_str = settings.get("allowed_free_roles", "").strip()
    if not allowed_roles_str:
        # If no role is configured, all members can use it
        return True, ""

    allowed_role_ids = [int(r.strip()) for r in allowed_roles_str.split(",") if r.strip().isdigit()]
    if not allowed_role_ids:
        return True, ""

    # 4. Check if member has at least one of the allowed roles
    if hasattr(user, "roles"):
        user_role_ids = {r.id for r in user.roles}
        if any(rid in user_role_ids for rid in allowed_role_ids):
            return True, ""

    # Format allowed roles for notification
    roles_display = ", ".join([f"<@&{rid}>" for rid in allowed_role_ids])
    return False, roles_display

def create_free_panel_embed() -> discord.Embed:
    settings = database.get_all_settings()
    bot_name = settings.get("bot_name", "GLOBAL BYPASS")
    color_hex = settings.get("free_color", "00FFA2")
    embed_color = parse_hex_color(color_hex, 0x00FFA2)

    used_count = database.get_used_count("FREE")
    available_count = database.get_available_count("FREE")
    total_capacity = used_count + available_count
    # Match the reference image: e.g. 0/9999 or actual
    total_display = total_capacity if total_capacity > 0 else 9999
    max_days = settings.get("max_days", "1")
    per_person_limit = settings.get("free_limit_per_person", "1")

    embed = discord.Embed(
        title=f"{bot_name} | Free Access",
        color=embed_color,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )

    description_text = (
        "**Free Access**\n\n"
        "**Generate a free temporary account.**\n\n"
        f"```yaml\n"
        f"Users used: {used_count}/{total_display}\n"
        f"Available: {available_count}\n"
        f"Maximum days: {max_days}\n"
        f"Per-person limit: {per_person_limit}\n"
        f"```"
    )

    embed.description = description_text
    embed.set_footer(text="Free access | Limited use")
    
    # Attach dragon logo as thumbnail
    import os
    if os.path.exists("assets/logo.png"):
        embed.set_thumbnail(url="attachment://logo.png")
        
    return embed

class FreePanelView(View):
    def __init__(self):
        super().__init__(timeout=None) # Persistent view

    @discord.ui.button(
        label="Generate User",
        style=discord.ButtonStyle.success,
        emoji="🎁",
        custom_id="btn_free_generate_user"
    )
    async def generate_user_button(self, interaction: discord.Interaction, button: Button):
        # Role-based permission check
        allowed, req_roles = check_user_role_access(interaction)
        if not allowed:
            await interaction.response.send_message(
                f"⛔ **Access Denied!**\n"
                f"You do not have the required role to use this bot.\n"
                f"**Required Role(s):** {req_roles}",
                ephemeral=True
            )
            return

        user_id = interaction.user.id
        now_ts = time.time()

        # Cooldown check
        if user_id in COOLDOWNS:
            diff = now_ts - COOLDOWNS[user_id]
            if diff < COOLDOWN_SECONDS:
                remaining = round(COOLDOWN_SECONDS - diff, 1)
                await interaction.response.send_message(
                    f"⏳ Rate limited! Please wait **{remaining}s** before trying again.",
                    ephemeral=True
                )
                return

        COOLDOWNS[user_id] = now_ts

        # Attempt to claim key
        success, key_or_err, password, expires_at = database.claim_free_key(user_id, str(interaction.user))

        if not success:
            if key_or_err == "LIMIT_REACHED":
                await interaction.response.send_message(
                    "❌ **Limit Reached!** You have already generated your free key.\n"
                    "👉 Click **View User** to see your existing credentials.",
                    ephemeral=True
                )
            elif key_or_err == "OUT_OF_STOCK":
                await interaction.response.send_message(
                    "❌ **Out of Stock!** There are currently no keys available in stock.\n"
                    "Please wait for an administrator to feed more keys.",
                    ephemeral=True
                )
            elif key_or_err == "BOT_DISABLED":
                await interaction.response.send_message(
                    "❌ The generator is temporarily disabled by administrators.",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"❌ An error occurred: `{key_or_err}`",
                    ephemeral=True
                )
            return

        settings = database.get_all_settings()
        max_days = settings.get("max_days", "1")
        pwd_display = f"`{password}`" if password else "*No password required*"

        # Form DM message
        dm_content = (
            f"🎉 **Your Free Account / Key has been generated!**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔑 **Key:** `{key_or_err}`\n"
            f"🔒 **Password:** {pwd_display}\n"
            f"⏳ **Duration:** {max_days} Day(s)\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚠️ *Please store this safely. You can also view it anytime with the 'View User' button.*"
        )

        dm_sent = False
        try:
            await interaction.user.send(dm_content)
            dm_sent = True
        except (discord.Forbidden, discord.HTTPException):
            dm_sent = False

        # Ephemeral response to user in Discord channel
        dm_note = "✅ Credentials have also been sent to your DMs!" if dm_sent else "⚠️ *Your DMs are disabled/closed, so please copy the credentials above!*"
        ephemeral_msg = (
            f"🎉 **Success! Your Free Key has been generated:**\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔑 **Key:** `{key_or_err}`\n"
            f"🔒 **Password:** {pwd_display}\n"
            f"⏳ **Duration:** {max_days} Day(s)\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"{dm_note}"
        )
        await interaction.response.send_message(ephemeral_msg, ephemeral=True)

        # Update the panel embed counts dynamically
        try:
            new_embed = create_free_panel_embed()
            await interaction.message.edit(embed=new_embed, view=self)
        except Exception as e:
            print(f"Error updating panel embed: {e}")

        # Send audit log to FREE logs and Admin logs channels
        bot = interaction.client
        free_logs_id = int(settings.get("free_logs", "0") or 0)
        admin_logs_id = int(settings.get("admin_panel_logs", "0") or 0)

        log_embed = discord.Embed(
            title="📥 Free Key Claimed",
            color=0x00FFA2,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        log_embed.add_field(name="User", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=False)
        log_embed.add_field(name="Key", value=f"`{key_or_err}`", inline=True)
        log_embed.add_field(name="Password", value=pwd_display, inline=True)
        log_embed.add_field(name="Available Stock", value=str(database.get_available_count("FREE")), inline=True)
        log_embed.set_footer(text=f"Claimed by {interaction.user}")

        # Send to FREE logs
        if free_logs_id and free_logs_id != 0:
            free_channel = bot.get_channel(free_logs_id)
            if free_channel:
                try:
                    await free_channel.send(embed=log_embed)
                except Exception as ex:
                    print(f"Failed to send to free logs channel: {ex}")

        # Send to Admin logs
        if admin_logs_id and admin_logs_id != 0 and admin_logs_id != free_logs_id:
            admin_channel = bot.get_channel(admin_logs_id)
            if admin_channel:
                try:
                    await admin_channel.send(embed=log_embed)
                except Exception as ex:
                    print(f"Failed to send to admin logs channel: {ex}")

    @discord.ui.button(
        label="View User",
        style=discord.ButtonStyle.primary,
        emoji="🔍",
        custom_id="btn_free_view_user"
    )
    async def view_user_button(self, interaction: discord.Interaction, button: Button):
        # Role-based permission check
        allowed, req_roles = check_user_role_access(interaction)
        if not allowed:
            await interaction.response.send_message(
                f"⛔ **Access Denied!**\n"
                f"You do not have the required role to use this bot.\n"
                f"**Required Role(s):** {req_roles}",
                ephemeral=True
            )
            return

        user_id = interaction.user.id
        record = database.get_user_active_key(user_id, "FREE")

        if not record:
            await interaction.response.send_message(
                "❌ **No Key Found!** You haven't generated any free key yet.\n"
                "👉 Click **Generate User** to get your free key.",
                ephemeral=True
            )
            return

        key_val = record["key_value"]
        pwd_val = record["password"]
        pwd_display = f"`{pwd_val}`" if pwd_val else "*None*"
        claimed_at = record["claimed_at"]
        expires_at = record.get("expires_at", "N/A")

        embed = discord.Embed(
            title="📋 Your Active Free Key",
            color=0x3B82F6,
            description="Here are the credentials for your current active account:"
        )
        embed.add_field(name="🔑 Key", value=f"```{key_val}```", inline=False)
        embed.add_field(name="🔒 Password", value=f"```{pwd_val if pwd_val else 'None'}```", inline=False)
        embed.add_field(name="📅 Claimed At", value=f"`{claimed_at}`", inline=True)
        embed.add_field(name="⏳ Expires At", value=f"`{expires_at}`", inline=True)
        embed.set_footer(text="Keep your credentials private!")

        await interaction.response.send_message(embed=embed, ephemeral=True)
