import discord
from discord.ext import commands
from discord import app_commands
import database
from views.free_panel import FreePanelView, create_free_panel_embed
from views.admin_panel import AdminPanelView, create_admin_panel_embed, is_admin
from views.modals import parse_input_keys, FeedKeysModal

class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_check(self, ctx: commands.Context) -> bool:
        return is_admin(ctx.author)

    @app_commands.command(name="panel_free", description="Deploy the Free Access panel to a channel.")
    @app_commands.describe(channel="Channel where the Free Access panel should be sent (defaults to current channel)")
    async def panel_free(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        if not is_admin(interaction.user):
            await interaction.response.send_message("⛔ You do not have permission to use this command.", ephemeral=True)
            return

        target_ch = channel or interaction.channel
        embed = create_free_panel_embed()
        import os
        if os.path.exists("assets/logo.png"):
            file = discord.File("assets/logo.png", filename="logo.png")
            msg = await target_ch.send(file=file, embed=embed, view=FreePanelView())
        else:
            msg = await target_ch.send(embed=embed, view=FreePanelView())

        database.set_setting("free_channel", str(target_ch.id))
        database.set_setting("free_panel_message_id", str(msg.id))

        await interaction.response.send_message(f"✅ Free Access Panel sent to {target_ch.mention}!", ephemeral=True)

    @app_commands.command(name="panel_admin", description="Deploy the Settings / Admin panel.")
    @app_commands.describe(channel="Admin channel to send the settings panel (defaults to current channel)")
    async def panel_admin(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        if not is_admin(interaction.user):
            await interaction.response.send_message("⛔ You do not have permission to use this command.", ephemeral=True)
            return

        target_ch = channel or interaction.channel
        embed = create_admin_panel_embed()
        import os
        if os.path.exists("assets/logo.png"):
            file = discord.File("assets/logo.png", filename="logo.png")
            msg = await target_ch.send(file=file, embed=embed, view=AdminPanelView())
        else:
            msg = await target_ch.send(embed=embed, view=AdminPanelView())

        database.set_setting("admin_panel_channel", str(target_ch.id))
        database.set_setting("admin_panel_message_id", str(msg.id))

        await interaction.response.send_message(f"✅ Settings Panel sent to {target_ch.mention}!", ephemeral=True)

    @app_commands.command(name="feed_keys", description="Feed keys with optional passwords into the stock.")
    @app_commands.describe(
        tier="Choose FREE or PAID tier",
        keys="Raw keys (e.g. key1:pass1, key2:pass2 or KEY1, KEY2)"
    )
    @app_commands.choices(tier=[
        app_commands.Choice(name="FREE", value="FREE"),
        app_commands.Choice(name="PAID", value="PAID")
    ])
    async def feed_keys(self, interaction: discord.Interaction, tier: str = "FREE", keys: str = ""):
        if not is_admin(interaction.user):
            await interaction.response.send_message("⛔ You do not have permission to use this command.", ephemeral=True)
            return

        if not keys:
            await interaction.response.send_modal(FeedKeysModal(tier=tier))
            return

        parsed = parse_input_keys(keys)
        if not parsed:
            await interaction.response.send_message("❌ No valid keys detected.", ephemeral=True)
            return

        added, duplicates = database.add_keys(parsed, tier=tier)
        database.log_audit(
            interaction.user.id,
            str(interaction.user),
            f"FEED_{tier}_KEYS",
            f"Added {added} keys, {duplicates} duplicates"
        )

        embed = discord.Embed(
            title="✅ Keys Fed Successfully",
            color=0x00FF88,
            description=f"**Tier:** `{tier}`\n**Added:** `{added}`\n**Duplicates:** `{duplicates}`\n**Available Stock:** `{database.get_available_count(tier)}`"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="generate_keys", description="Auto-generate random keys and passwords into stock.")
    @app_commands.describe(
        count="Number of keys to generate",
        prefix="Key prefix (e.g. GB- or VIP-)",
        tier="Tier (FREE or PAID)",
        with_password="Generate companion passwords?"
    )
    @app_commands.choices(tier=[
        app_commands.Choice(name="FREE", value="FREE"),
        app_commands.Choice(name="PAID", value="PAID")
    ])
    async def generate_keys(self, interaction: discord.Interaction, count: int, prefix: str = "GB-", tier: str = "FREE", with_password: bool = True):
        if not is_admin(interaction.user):
            await interaction.response.send_message("⛔ You do not have permission to use this command.", ephemeral=True)
            return

        if count <= 0 or count > 500:
            await interaction.response.send_message("❌ Count must be between 1 and 500.", ephemeral=True)
            return

        added = database.generate_random_keys(count, prefix=prefix, tier=tier, with_password=with_password)
        database.log_audit(
            interaction.user.id,
            str(interaction.user),
            f"GENERATE_{tier}_KEYS",
            f"Generated {added} keys"
        )

        embed = discord.Embed(
            title="⚡ Keys Generated",
            color=0x00FF88,
            description=f"Generated and added **{added}** keys to **{tier}** stock!\nAvailable now: `{database.get_available_count(tier)}`"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="reset_limits", description="Reset free user limits for all users or a specific user.")
    @app_commands.describe(user="Optional user to reset. If left empty, all free limits are reset.")
    async def reset_limits(self, interaction: discord.Interaction, user: discord.Member = None):
        if not is_admin(interaction.user):
            await interaction.response.send_message("⛔ You do not have permission to use this command.", ephemeral=True)
            return

        if user:
            database.reset_single_user_limit(user.id)
            database.log_audit(interaction.user.id, str(interaction.user), "RESET_USER_LIMIT", f"Reset limit for {user.id}")
            await interaction.response.send_message(f"✅ Reset FREE limit for {user.mention}.", ephemeral=True)
        else:
            database.reset_all_free_limits()
            database.log_audit(interaction.user.id, str(interaction.user), "RESET_ALL_LIMITS", "Reset limits for all users")
            await interaction.response.send_message("✅ Reset FREE limits for **ALL** users! Everyone can generate a free key again.", ephemeral=True)

    @app_commands.command(name="delete_user", description="Revoke a user's active key and remove their claim.")
    @app_commands.describe(user="The member to delete")
    async def delete_user(self, interaction: discord.Interaction, user: discord.Member):
        if not is_admin(interaction.user):
            await interaction.response.send_message("⛔ You do not have permission to use this command.", ephemeral=True)
            return

        deleted = database.delete_user_records(user.id)
        if deleted:
            database.log_audit(interaction.user.id, str(interaction.user), "DELETE_USER", f"Deleted {user.id}")
            await interaction.response.send_message(f"✅ Records deleted and keys revoked for {user.mention}.", ephemeral=True)
        else:
            await interaction.response.send_message(f"⚠️ No active claims found for {user.mention}.", ephemeral=True)

    @app_commands.command(name="stock", description="Check current key inventory and usage statistics.")
    async def stock(self, interaction: discord.Interaction):
        free_avail = database.get_available_count("FREE")
        free_used = database.get_used_count("FREE")
        paid_avail = database.get_available_count("PAID")
        paid_used = database.get_used_count("PAID")

        embed = discord.Embed(
            title="📊 Key Inventory & Usage",
            color=0x3B82F6
        )
        embed.add_field(
            name="🎁 FREE Keys",
            value=f"• Available: `{free_avail}`\n• Claimed: `{free_used}`\n• Total: `{free_avail + free_used}`",
            inline=True
        )
        embed.add_field(
            name="💳 PAID Keys",
            value=f"• Available: `{paid_avail}`\n• Claimed: `{paid_used}`\n• Total: `{paid_avail + paid_used}`",
            inline=True
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="set_role", description="Configure which role is authorized to use the bot.")
    @app_commands.describe(
        role="The Discord role required to use the bot (leave empty to reset to Everyone)",
        tier="Which access tier to apply to (FREE or PAID)"
    )
    @app_commands.choices(tier=[
        app_commands.Choice(name="FREE", value="FREE"),
        app_commands.Choice(name="PAID", value="PAID")
    ])
    async def set_role(self, interaction: discord.Interaction, role: discord.Role = None, tier: str = "FREE"):
        if not is_admin(interaction.user):
            await interaction.response.send_message("⛔ You do not have permission to use this command.", ephemeral=True)
            return

        key = "allowed_free_roles" if tier == "FREE" else "allowed_paid_roles"
        if role is None:
            database.set_setting(key, "")
            await interaction.response.send_message(f"✅ Role restriction removed for **{tier}**. **Everyone** can now use the bot.", ephemeral=True)
        else:
            database.set_setting(key, str(role.id))
            await interaction.response.send_message(
                f"✅ **Role restriction set!**\n"
                f"Only members with {role.mention} (`{role.id}`) are authorized to use **{tier}** bot features.\n"
                f"Other members can view the panel, but will be denied access if they try to use it.",
                ephemeral=True
            )

    @app_commands.command(name="setup", description="Configure bot channels, roles, and logging.")
    @app_commands.describe(
        free_channel="Channel for Free Access Panel",
        free_logs="Channel for Free key claim logs",
        admin_logs="Channel for Admin panel logs",
        paid_channel="Channel for Paid access",
        paid_logs="Channel for Paid logs",
        free_role="Role required to use the Free bot features",
        paid_role="Role required for Paid access"
    )
    async def setup(
        self,
        interaction: discord.Interaction,
        free_channel: discord.TextChannel = None,
        free_logs: discord.TextChannel = None,
        admin_logs: discord.TextChannel = None,
        paid_channel: discord.TextChannel = None,
        paid_logs: discord.TextChannel = None,
        free_role: discord.Role = None,
        paid_role: discord.Role = None
    ):
        if not is_admin(interaction.user):
            await interaction.response.send_message("⛔ You do not have permission to use this command.", ephemeral=True)
            return

        updates = []
        if free_channel:
            database.set_setting("free_channel", str(free_channel.id))
            updates.append(f"Free Channel: {free_channel.mention}")
        if free_logs:
            database.set_setting("free_logs", str(free_logs.id))
            updates.append(f"Free Logs: {free_logs.mention}")
        if admin_logs:
            database.set_setting("admin_panel_logs", str(admin_logs.id))
            updates.append(f"Admin Logs: {admin_logs.mention}")
        if paid_channel:
            database.set_setting("paid_channel", str(paid_channel.id))
            updates.append(f"Paid Channel: {paid_channel.mention}")
        if paid_logs:
            database.set_setting("paid_logs", str(paid_logs.id))
            updates.append(f"Paid Logs: {paid_logs.mention}")
        if free_role:
            database.set_setting("allowed_free_roles", str(free_role.id))
            updates.append(f"Allowed FREE Role: {free_role.mention}")
        if paid_role:
            database.set_setting("allowed_paid_roles", str(paid_role.id))
            updates.append(f"Allowed PAID Role: {paid_role.mention}")

        if not updates:
            await interaction.response.send_message("⚠️ No channels or roles specified to update.", ephemeral=True)
            return

        embed = discord.Embed(
            title="⚙️ Configuration Updated",
            color=0x00FF88,
            description="\n".join([f"• {u}" for u in updates])
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(AdminCog(bot))
