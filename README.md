# GLOBAL BYPASS - Discord Key & Account Distribution Bot

A Discord Key Distribution & Administration Bot built with `discord.py` 2.x and Python 3.14. Features an interactive **Free Access Panel** with key claiming, rate limiting, and 1-key-per-user enforcement, alongside an **Admin / Settings Panel** with real-time settings management, key feeding, and auto-generation.

---

## 📸 Reference Panels

1. **Free Access Panel**
   - Live real-time counters: `Users used`, `Available`, `Maximum days`, `Per-person limit`.
   - 🎁 **Generate User**: Claims 1 key from inventory, delivers credentials via DM + Ephemeral chat, logs to channel, and updates the public panel.
   - 🔍 **View User**: Allows users to review their active key and password anytime.

2. **Admin / Settings Panel**
   - Overview of Bot Name, Status, Stock, Logs, Channels, Colors, and Limits.
   - ✏️ **Name**: Modal to update bot display title.
   - 🎨 **Colors**: Modal to customize HEX colors for panels.
   - ➕ **Feed Keys**: Multi-format key import (comma-separated, `key:password`, `key,password`, or line-by-line).
   - ⚡ **Auto Gen Keys**: Cryptographic random key & password generator.
   - 🔄 **Reset FREE limits**: Instantly reset limits globally or for specific users.
   - 🗑️ **Delete User**: Revoke user keys and clear limits.
   - 📋 **FREE / PAID Lists**: View recent claims and assigned accounts.
   - 📢 **Deploy Free Panel**: Automatically post and link the access panel.

---

## 🚀 Quick Start (Local Run)

### 1. Requirements
- Python 3.10+ (tested and verified on Python 3.14)
- Pip dependencies installed:
  ```bash
  pip install -r requirements.txt
  ```

### 2. Configuration
Copy `.env.example` to `.env` (or use the pre-configured `.env`):
```env
DISCORD_BOT_TOKEN=your_bot_token_here
PORT=8080
BOT_NAME=GLOBAL BYPASS
SUPPORT_URL=https://discord.gg/
```

### 3. Run the Bot
```bash
python bot.py
```

---

## 🔗 Adding Bot to Your Discord Server

Use this authorization link to invite the bot with required permissions:
```
https://discord.com/oauth2/authorize?client_id=1567015043336241213&permissions=8&scope=bot%20applications.commands
```
*(Make sure the **Server Members Intent** and **Message Content Intent** are enabled in the Discord Developer Portal under Bot settings)*

---

## 🌐 Deploying to Render (24/7 Hosting)

The project includes built-in keep-alive web server (`server.py`) and `render.yaml` configuration for zero-downtime hosting on Render.

### Steps:
1. Push this repository to your **GitHub** account:
   ```bash
   git init
   git add .
   git commit -m "Initial commit of Global Bypass Bot"
   git remote add origin https://github.com/your-username/global-bypass-bot.git
   git push -u origin main
   ```
2. Log in to [Render Dashboard](https://dashboard.render.com/).
3. Click **New +** -> **Web Service**.
4. Connect your GitHub repository.
5. Configure:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`
6. Add Environment Variable in Render:
   - Key: `DISCORD_BOT_TOKEN`
   - Value: `your_discord_bot_token_here`
7. Click **Create Web Service**. Render will build and deploy the bot immediately!

---

## 📋 Slash Commands Reference

| Command | Description | Permissions |
|---|---|---|
| `/panel_free [channel]` | Sends the Free Access panel with buttons | Admin / Owner |
| `/panel_admin [channel]` | Sends the real-time Admin Settings panel | Admin / Owner |
| `/feed_keys [tier] [keys]` | Feed raw keys and passwords into stock | Admin / Owner |
| `/generate_keys [count] [prefix] [tier]` | Generate batch cryptographic keys into stock | Admin / Owner |
| `/stock` | View available and claimed key statistics | Everyone |
| `/reset_limits [user]` | Reset free limits (all users or specific user) | Admin / Owner |
| `/delete_user <user>` | Revoke user key and clear user claim | Admin / Owner |
| `/set_role [role] [tier]` | Restrict bot usage to a specific Discord role (leave empty for Everyone) | Admin / Owner |
| `/join_vc [channel]` | Join a voice channel and keep 24/7 presence with auto-reconnect | Admin / Owner |
| `/leave_vc` | Disconnect from the voice channel and disable 24/7 VC | Admin / Owner |
| `/setup [free_channel] [logs] [voice_channel]...` | Configure Discord channels, voice, and roles | Admin / Owner |

---

## 👥 Role-Based Access Control (Exclusive Access)
- **Public Visibility, Restricted Action**: The panels can be posted in any channel visible to all server members.
- **Role Enforcement**: Only users who possess the configured role (e.g. via `/set_role role:@Member` or via the **🛡️ Admin** modal in the Settings panel) can interact with **🎁 Generate User** and **🔍 View User**.
- **Ephemeral Rejection**: If an unauthorized user clicks a button, the bot responds privately to them: `⛔ Access Denied! You do not have the required role to use this bot. Required Role(s): <@&role_id>`.
- **Admin Bypass**: Server Administrators and designated Admin Panel Owners can always use and test the bot regardless of role restrictions.

---

## 🔑 Key Feeding Formats Supported

The Feed Keys modal and command accept all common formats:
- `KEY1:PASS1, KEY2:PASS2`
- `KEY1,PASS1`
- `KEY1` (without password)
- Multiline paste (e.g. 50 keys at once from a file or generator)
- Automatic duplicate detection prevents duplicate keys from being added.

---

## 🛡️ Anti-Spam & Rate Limiting
- Built-in button cooldowns prevent rapid spam-clicking.
- Database transactions enforce atomic single-claim per user.
- DMs are attempted first, followed by safe ephemeral chat fallback if a user has their direct messages closed.
