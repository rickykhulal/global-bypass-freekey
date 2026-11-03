import discord
from discord.ui import Modal, TextInput
import database

def parse_input_keys(raw_text: str) -> list[dict]:
    """
    Parses input text in multiple formats:
    - key:password
    - key,password
    - key alone
    - separated by newlines or commas
    """
    results = []
    # Normalize newlines
    normalized = raw_text.replace("\r", "")
    lines = normalized.split("\n")
    tokens = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # If line contains both commas and colons, e.g. "key1:pass1, key2:pass2"
        # or multiple comma-separated keys "k1, k2, k3"
        if "," in line:
            subparts = [p.strip() for p in line.split(",") if p.strip()]
            # If each subpart looks like key:pass or plain key
            if any(":" in sp for sp in subparts) or len(subparts) > 2:
                tokens.extend(subparts)
            else:
                # Exactly 2 parts without colons -> "KEY, PASSWORD"
                tokens.append(line)
        else:
            tokens.append(line)

    for item in tokens:
        if not item:
            continue
        if ":" in item:
            parts = item.split(":", 1)
            results.append({"key": parts[0].strip(), "password": parts[1].strip()})
        elif "," in item and item.count(",") == 1:
            parts = item.split(",", 1)
            results.append({"key": parts[0].strip(), "password": parts[1].strip()})
        else:
            results.append({"key": item.strip(), "password": ""})
            
    return results

class FeedKeysModal(Modal):
    def __init__(self, tier: str = "FREE"):
        super().__init__(title=f"Feed {tier} Keys & Passwords")
        self.tier = tier

        self.keys_input = TextInput(
            label="Keys & Passwords",
            style=discord.TextStyle.paragraph,
            placeholder="Formats accepted:\nKEY:PASS\nKEY,PASS\nor multiple separated by newlines or commas",
            required=True,
            max_length=4000
        )
        self.add_item(self.keys_input)

    async def on_submit(self, interaction: discord.Interaction):
        parsed = parse_input_keys(self.keys_input.value)
        if not parsed:
            await interaction.response.send_message("❌ No valid keys detected in your input.", ephemeral=True)
            return

        added, duplicates = database.add_keys(parsed, tier=self.tier)
        database.log_audit(
            interaction.user.id,
            str(interaction.user),
            f"FEED_{self.tier}_KEYS",
            f"Added {added} keys, {duplicates} duplicates"
        )

        embed = discord.Embed(
            title="✅ Keys Fed Successfully",
            color=0x00FF88,
            description=f"**Tier:** `{self.tier}`\n**Added:** `{added}`\n**Duplicates Skipped:** `{duplicates}`\n**Total Available:** `{database.get_available_count(self.tier)}`"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class AutoGenerateKeysModal(Modal):
    def __init__(self, tier: str = "FREE"):
        super().__init__(title=f"Auto-Generate {tier} Keys")
        self.tier = tier

        self.count_input = TextInput(
            label="How many keys to generate?",
            style=discord.TextStyle.short,
            placeholder="e.g. 10, 50, 100",
            default="10",
            required=True,
            max_length=5
        )
        self.add_item(self.count_input)

        self.prefix_input = TextInput(
            label="Key Prefix",
            style=discord.TextStyle.short,
            placeholder="e.g. GB- or FREE-",
            default="GB-",
            required=False,
            max_length=15
        )
        self.add_item(self.prefix_input)

        self.password_input = TextInput(
            label="Generate Random Passwords? (yes/no)",
            style=discord.TextStyle.short,
            placeholder="yes or no",
            default="yes",
            required=True,
            max_length=5
        )
        self.add_item(self.password_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            count = int(self.count_input.value.strip())
            if count <= 0 or count > 500:
                await interaction.response.send_message("❌ Please enter a count between 1 and 500.", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("❌ Invalid number provided for count.", ephemeral=True)
            return

        prefix = self.prefix_input.value.strip() or "GB-"
        with_pwd = self.password_input.value.strip().lower() in ["yes", "y", "true", "1"]

        added = database.generate_random_keys(count, prefix=prefix, tier=self.tier, with_password=with_pwd)
        database.log_audit(
            interaction.user.id,
            str(interaction.user),
            f"GENERATE_{self.tier}_KEYS",
            f"Generated {added} keys with prefix {prefix}"
        )

        embed = discord.Embed(
            title="⚡ Keys Generated",
            color=0x00FF88,
            description=f"Generated and added **{added}** random keys to **{self.tier}** stock!\nAvailable now: `{database.get_available_count(self.tier)}`"
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class BotNameModal(Modal, title="Change Bot Name"):
    name_input = TextInput(
        label="Bot Name",
        style=discord.TextStyle.short,
        placeholder="Enter bot title (e.g. GLOBAL BYPASS)",
        default="GLOBAL BYPASS",
        required=True,
        max_length=50
    )

    async def on_submit(self, interaction: discord.Interaction):
        new_name = self.name_input.value.strip()
        database.set_setting("bot_name", new_name)
        await interaction.response.send_message(f"✅ Bot name updated to **{new_name}**.", ephemeral=True)

class ColorsModal(Modal, title="Configure Embed Colors"):
    free_color = TextInput(
        label="FREE Panel Color (HEX)",
        style=discord.TextStyle.short,
        placeholder="e.g. 00FFA2 or #00FFA2",
        default="00FFA2",
        required=True,
        max_length=10
    )
    paid_color = TextInput(
        label="PAID Panel Color (HEX)",
        style=discord.TextStyle.short,
        placeholder="e.g. FF9900 or Not configured",
        default="Not configured",
        required=False,
        max_length=20
    )
    admin_color = TextInput(
        label="Admin Panel Color (HEX)",
        style=discord.TextStyle.short,
        placeholder="e.g. FC2403",
        default="FC2403",
        required=True,
        max_length=10
    )

    def __init__(self):
        super().__init__()
        settings = database.get_all_settings()
        self.free_color.default = settings.get("free_color", "00FFA2")
        self.paid_color.default = settings.get("paid_color", "Not configured")
        self.admin_color.default = settings.get("admin_panel_color", "FC2403")

    async def on_submit(self, interaction: discord.Interaction):
        fc = self.free_color.value.strip().replace("#", "")
        pc = self.paid_color.value.strip().replace("#", "")
        ac = self.admin_color.value.strip().replace("#", "")

        database.set_setting("free_color", fc)
        database.set_setting("paid_color", pc)
        database.set_setting("admin_panel_color", ac)

        await interaction.response.send_message("✅ Embed colors saved successfully! Click **Refresh** to see changes.", ephemeral=True)

class FreeConfigModal(Modal, title="Configure FREE Access Limits"):
    limit_input = TextInput(
        label="Per-Person Limit",
        style=discord.TextStyle.short,
        placeholder="e.g. 1",
        default="1",
        required=True,
        max_length=5
    )
    days_input = TextInput(
        label="Maximum Days Duration",
        style=discord.TextStyle.short,
        placeholder="e.g. 1",
        default="1",
        required=True,
        max_length=5
    )

    def __init__(self):
        super().__init__()
        settings = database.get_all_settings()
        self.limit_input.default = settings.get("free_limit_per_person", "1")
        self.days_input.default = settings.get("max_days", "1")

    async def on_submit(self, interaction: discord.Interaction):
        try:
            lim = int(self.limit_input.value.strip())
            days = int(self.days_input.value.strip())
            if lim < 1 or days < 1:
                raise ValueError()
        except ValueError:
            await interaction.response.send_message("❌ Please enter valid positive integers.", ephemeral=True)
            return

        database.set_setting("free_limit_per_person", str(lim))
        database.set_setting("max_days", str(days))
        await interaction.response.send_message(f"✅ Free settings updated: Limit per person = `{lim}`, Duration = `{days}` day(s).", ephemeral=True)

class AdminConfigModal(Modal, title="Configure Admins & Roles"):
    admin_owners_input = TextInput(
        label="Admin Owner IDs (comma separated)",
        style=discord.TextStyle.paragraph,
        placeholder="e.g. 1392630988622008352, 1190844956395446397",
        required=False,
        max_length=1000
    )
    allowed_roles_input = TextInput(
        label="Allowed PAID Roles IDs (comma separated)",
        style=discord.TextStyle.paragraph,
        placeholder="e.g. 1560655816477114509",
        required=False,
        max_length=1000
    )

    def __init__(self):
        super().__init__()
        settings = database.get_all_settings()
        self.admin_owners_input.default = settings.get("admin_panel_owners", "")
        self.allowed_roles_input.default = settings.get("allowed_paid_roles", "")

    async def on_submit(self, interaction: discord.Interaction):
        database.set_setting("admin_panel_owners", self.admin_owners_input.value.strip())
        database.set_setting("allowed_paid_roles", self.allowed_roles_input.value.strip())
        await interaction.response.send_message("✅ Admin owners and allowed roles saved.", ephemeral=True)

class DeleteUserModal(Modal, title="Delete / Revoke User"):
    user_id_input = TextInput(
        label="Target Discord User ID",
        style=discord.TextStyle.short,
        placeholder="e.g. 1392630988622008352",
        required=True,
        max_length=25
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            target_id = int(self.user_id_input.value.strip())
        except ValueError:
            await interaction.response.send_message("❌ Invalid user ID. It must be numeric.", ephemeral=True)
            return

        deleted = database.delete_user_records(target_id)
        if deleted:
            database.log_audit(
                interaction.user.id,
                str(interaction.user),
                "DELETE_USER",
                f"Deleted user claim for {target_id}"
            )
            await interaction.response.send_message(f"✅ Successfully deleted records and freed limits for user `{target_id}`.", ephemeral=True)
        else:
            await interaction.response.send_message(f"⚠️ No active claims found for user `{target_id}`.", ephemeral=True)
