import discord
from discord.ui import View, Button
import datetime
import database
from views.modals import (
    FeedKeysModal,
    AutoGenerateKeysModal,
    BotNameModal,
    ColorsModal,
    FreeConfigModal,
    AdminConfigModal,
    DeleteUserModal
)
from views.free_panel import parse_hex_color, FreePanelView, create_free_panel_embed

def is_admin(user: discord.User | discord.Member) -> bool:
    # Check guild administrator permission
    if isinstance(user, discord.Member) and user.guild_permissions.administrator:
        return True
    
    settings = database.get_all_settings()
    owners_str = settings.get("admin_panel_owners", "")
    owner_ids = [int(i.strip()) for i in owners_str.split(",") if i.strip().isdigit()]
    return user.id in owner_ids

def create_admin_panel_embed() -> discord.Embed:
    settings = database.get_all_settings()
    bot_name = settings.get("bot_name", "GLOBAL BYPASS")
    status = settings.get("status", "Enabled")
    total_limit = settings.get("total_limit", "INFINITE")
    
    paid_count = database.get_used_count("PAID")
    free_used = database.get_used_count("FREE")
    free_avail = database.get_available_count("FREE")
    free_total = free_used + free_avail
    total_display = free_total if free_total > 0 else 9999
    max_days = settings.get("max_days", "1")
    per_person_limit = settings.get("free_limit_per_person", "1")

    paid_ch = settings.get("paid_channel", "0")
    paid_logs = settings.get("paid_logs", "0")
    free_ch = settings.get("free_channel", "0")
    free_logs = settings.get("free_logs", "0")
    voice_ch = settings.get("voice_channel", "0")
    allowed_roles = settings.get("allowed_paid_roles", "None")
    paid_owners = settings.get("paid_owners", "None")
    admin_owners = settings.get("admin_panel_owners", "None")
    
    paid_color = settings.get("paid_color", "Not configured")
    free_color = settings.get("free_color", "00FFA2")
    admin_color_hex = settings.get("admin_panel_color", "FC2403")
    admin_logs = settings.get("admin_panel_logs", "0")
    language = settings.get("language", "English")

    color_int = parse_hex_color(admin_color_hex, 0xFC2403)

    embed = discord.Embed(
        title=f"{bot_name} | Settings",
        color=color_int,
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.description = "**Settings Panel**\nManage the bot settings in real time."

    embed.add_field(name="Bot name", value=f"`{bot_name}`", inline=True)
    embed.add_field(name="Status", value=f"`{status}`", inline=True)
    embed.add_field(name="Total limit (PAID + FREE)", value=f"`{total_limit}`", inline=True)

    embed.add_field(name="PAID users", value=f"`{paid_count}`", inline=True)
    embed.add_field(name="FREE users", value=f"`{free_used}/{total_display} | {max_days} maximum days`", inline=True)
    embed.add_field(name="FREE per-person limit", value=f"`{per_person_limit}`", inline=True)

    embed.add_field(name="PAID channel", value=f"`{paid_ch}`" if paid_ch != "0" else "`Not configured`", inline=True)
    embed.add_field(name="PAID logs", value=f"`{paid_logs}`" if paid_logs != "0" else "`Not configured`", inline=True)
    embed.add_field(name="FREE channel", value=f"`{free_ch}`" if free_ch != "0" else "`Not configured`", inline=True)

    embed.add_field(name="FREE logs", value=f"`{free_logs}`" if free_logs != "0" else "`Not configured`", inline=True)
    embed.add_field(name="Voice channel", value=f"`{voice_ch}`" if voice_ch != "0" else "`Not configured`", inline=True)
    embed.add_field(name="Allowed PAID roles", value=f"`{allowed_roles}`" if allowed_roles else "`None`", inline=True)

    embed.add_field(name="PAID owners", value=f"`{paid_owners}`" if paid_owners else "`None`", inline=True)
    embed.add_field(name="Admin panel owners", value=f"`{admin_owners}`" if admin_owners else "`None`", inline=True)
    embed.add_field(name="PAID color", value=f"`{paid_color}`", inline=True)

    embed.add_field(name="FREE color", value=f"`{free_color}`", inline=True)
    embed.add_field(name="Admin panel color", value=f"`{admin_color_hex}`", inline=True)
    embed.add_field(name="Admin panel logs", value=f"`{admin_logs}`" if admin_logs != "0" else "`Not configured`", inline=True)

    embed.add_field(name="Language", value=f"`{language}`", inline=True)

    import os
    if os.path.exists("assets/logo.png"):
        embed.set_thumbnail(url="attachment://logo.png")

    embed.set_footer(text="Not editable here: token, server, status, and total limit.")
    return embed

class AdminPanelView(View):
    def __init__(self):
        super().__init__(timeout=None) # Persistent view

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not is_admin(interaction.user):
            await interaction.response.send_message("⛔ You do not have permission to use the Admin Panel.", ephemeral=True)
            return False
        return True

    # ROW 1
    @discord.ui.button(label="Name", style=discord.ButtonStyle.primary, emoji="✏️", row=0, custom_id="admin_btn_name")
    async def name_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(BotNameModal())

    @discord.ui.button(label="Colors", style=discord.ButtonStyle.secondary, emoji="🎨", row=0, custom_id="admin_btn_colors")
    async def colors_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(ColorsModal())

    @discord.ui.button(label="PAID", style=discord.ButtonStyle.primary, emoji="💳", row=0, custom_id="admin_btn_paid")
    async def paid_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(FeedKeysModal(tier="PAID"))

    # ROW 2
    @discord.ui.button(label="FREE", style=discord.ButtonStyle.success, emoji="🎁", row=1, custom_id="admin_btn_free")
    async def free_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(FreeConfigModal())

    @discord.ui.button(label="Admin", style=discord.ButtonStyle.primary, emoji="🛡️", row=1, custom_id="admin_btn_admin")
    async def admin_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(AdminConfigModal())

    @discord.ui.button(label="Refresh", style=discord.ButtonStyle.primary, emoji="🔄", row=1, custom_id="admin_btn_refresh")
    async def refresh_btn(self, interaction: discord.Interaction, button: Button):
        embed = create_admin_panel_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    # ROW 3
    @discord.ui.button(label="PAID List", style=discord.ButtonStyle.primary, emoji="📋", row=2, custom_id="admin_btn_paid_list")
    async def paid_list_btn(self, interaction: discord.Interaction, button: Button):
        claims = database.get_claims_list("PAID", limit=15)
        if not claims:
            await interaction.response.send_message("📋 No PAID users have claimed keys yet.", ephemeral=True)
            return
        desc = "\n".join([f"• <@{c['user_id']}> (`{c['username']}`): `{c['key_value']}`" for c in claims])
        embed = discord.Embed(title="💳 Recent PAID Users", description=desc, color=0x3B82F6)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="FREE List", style=discord.ButtonStyle.secondary, emoji="📋", row=2, custom_id="admin_btn_free_list")
    async def free_list_btn(self, interaction: discord.Interaction, button: Button):
        claims = database.get_claims_list("FREE", limit=20)
        if not claims:
            await interaction.response.send_message("📋 No FREE users have claimed keys yet.", ephemeral=True)
            return
        desc = "\n".join([f"• <@{c['user_id']}> (`{c['username']}`): `{c['key_value']}` | {c['claimed_at'][:19]}" for c in claims])
        embed = discord.Embed(title="🎁 Recent FREE Users", description=desc, color=0x00FFA2)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Español", style=discord.ButtonStyle.secondary, emoji="🌐", row=2, custom_id="admin_btn_lang")
    async def lang_btn(self, interaction: discord.Interaction, button: Button):
        cur_lang = database.get_setting("language", "English")
        new_lang = "Español" if cur_lang == "English" else "English"
        database.set_setting("language", new_lang)
        button.label = "English" if new_lang == "Español" else "Español"
        embed = create_admin_panel_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Delete User", style=discord.ButtonStyle.danger, emoji="🗑️", row=2, custom_id="admin_btn_del_user")
    async def del_user_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(DeleteUserModal())

    @discord.ui.button(label="Reset FREE limits", style=discord.ButtonStyle.primary, emoji="🔄", row=2, custom_id="admin_btn_reset_free")
    async def reset_free_btn(self, interaction: discord.Interaction, button: Button):
        database.reset_all_free_limits()
        database.log_audit(interaction.user.id, str(interaction.user), "RESET_ALL_FREE_LIMITS", "Reset free claims limit for all users")
        await interaction.response.send_message("✅ **All FREE user limits have been reset!** Users can now generate another free key.", ephemeral=True)

    # ROW 4
    @discord.ui.button(label="Feed Keys", style=discord.ButtonStyle.success, emoji="➕", row=3, custom_id="admin_btn_feed_keys")
    async def feed_keys_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(FeedKeysModal(tier="FREE"))

    @discord.ui.button(label="Auto Gen Keys", style=discord.ButtonStyle.secondary, emoji="⚡", row=3, custom_id="admin_btn_auto_gen")
    async def auto_gen_btn(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(AutoGenerateKeysModal(tier="FREE"))

    @discord.ui.button(label="Deploy Free Panel", style=discord.ButtonStyle.primary, emoji="📢", row=3, custom_id="admin_btn_deploy_free")
    async def deploy_free_btn(self, interaction: discord.Interaction, button: Button):
        settings = database.get_all_settings()
        ch_id = int(settings.get("free_channel", "0") or 0)
        target_ch = interaction.guild.get_channel(ch_id) if ch_id else interaction.channel

        if not target_ch:
            await interaction.response.send_message("❌ Target channel not found. Please set Free Channel first.", ephemeral=True)
            return

        embed = create_free_panel_embed()
        import os
        if os.path.exists("assets/logo.png"):
            file = discord.File("assets/logo.png", filename="logo.png")
            msg = await target_ch.send(file=file, embed=embed, view=FreePanelView())
        else:
            msg = await target_ch.send(embed=embed, view=FreePanelView())
        database.set_setting("free_panel_message_id", str(msg.id))
        database.set_setting("free_channel", str(target_ch.id))
        await interaction.response.send_message(f"✅ Free Access Panel deployed in {target_ch.mention}!", ephemeral=True)
