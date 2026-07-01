# Discord Server Bot

A smart Python Discord bot that can build and organize a server, with:

- Slash commands
- Welcome messages
- Moderation logs
- Clear, warn, timeout, kick, and ban commands
- Persistent warnings stored in SQLite
- Private support tickets with buttons
- User and server information commands
- Rank sale logging to Google Sheets using a Discord form

## 1. Install Python

Install Python 3.11 or newer.

## 2. Create your Discord application

1. Open the Discord Developer Portal.
2. Create a **New Application**.
3. Open **Bot**, then create/add the bot user.
4. Under **Privileged Gateway Intents**, enable **Server Members Intent**.
5. Reset/copy the bot token. Never post the token publicly.
6. Open **OAuth2 → URL Generator**.
7. Select:
   - `bot`
   - `applications.commands`
8. Recommended bot permissions:
   - View Channels
   - Send Messages
   - Embed Links
   - Read Message History
   - Manage Messages
   - Moderate Members
   - Kick Members
   - Ban Members
   - Manage Channels
9. Open the generated URL and add the bot to your server.

## 3. Configure the project

Copy `.env.example` to a new file named `.env`.

Put the bot token after:

```env
DISCORD_TOKEN=
```

For faster command updates during testing:

1. Enable Discord Developer Mode.
2. Right-click your server and select **Copy Server ID**.
3. Put that number after `TEST_GUILD_ID=`.

## 4. Install and run

### Windows

```powershell
py -m venv .venv
.venv\Scripts\activate
py -m pip install -r requirements.txt
py bot.py
```

### Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 bot.py
```

## 5. Configure inside Discord

Run these commands as an administrator:

- `/setup_welcome #welcome`
- `/setup_logs #mod-logs`
- `/setup_tickets Tickets @Support`
- `/ticketpanel`

## Rank sale logging

Use `/rank-sale` to open a small Discord form. The form asks for:

- Seller Habbo Username
- Buyer Habbo Username
- Rank Sold
- Amount Paid
- Proof / Notes

The bot saves each submission to Google Sheets and also posts a clean embed in the rank-sales log channel.

### Google Sheet headers

Create a sheet tab named `Rank Sales` and use these columns:

```text
Timestamp | Seller Discord | Seller ID | Seller Habbo | Buyer | Rank | Amount | Proof/Notes | Channel | Channel ID
```

### Railway variables needed

Add these in Railway under your service **Variables** tab:

```env
DISCORD_TOKEN=your_discord_bot_token
TEST_GUILD_ID=your_discord_server_id
SPREADSHEET_ID=your_google_sheet_id
GOOGLE_CREDENTIALS_JSON=your_full_google_service_account_json
RANK_SALES_CHANNEL_ID=your_rank_sales_channel_id
SALES_ROLE_ID=optional_role_id_allowed_to_use_rank_sale
RANK_SALES_SHEET_NAME=Rank Sales
TIMEZONE=America/Chicago
```

`SALES_ROLE_ID` is optional. If you leave it blank, anyone who can see the command can submit the form. Administrators can always use the command.

Share the Google Sheet with the `client_email` from your Google service account JSON as **Editor**.

## Railway deployment

This repo includes `railway.toml`, so Railway starts the bot with:

```bash
python bot.py
```

Deploy from GitHub, add the Railway variables, then redeploy the service.

## Commands

- `/ping`
- `/rank-sale`
- `/userinfo`
- `/serverinfo`
- `/clear`
- `/warn`
- `/warnings`
- `/timeout`
- `/kick`
- `/ban`
- `/setup_welcome`
- `/setup_logs`
- `/setup_tickets`
- `/ticketpanel`

## Security

Never share your token or upload your `.env` file. If a token is exposed, reset it immediately in the Developer Portal.

## Smart server commands

- `/build_server` — Creates an organized Gaming, Community, or Business layout.
- `/server_audit` — Checks for missing channels, duplicates, empty categories, and permission risks.
- `/create_rules` — Posts a professional rules message.
- `/ask_organizer` — Uses optional AI to recommend improvements based on the current server structure.

### Recommended first setup

Give the bot these permissions and place its role high enough in the role list:

- Manage Channels
- Manage Roles
- Manage Messages
- Moderate Members
- Kick Members
- Ban Members
- View Audit Log

Then run:

```text
/build_server template:Gaming server
/server_audit
/ticketpanel
```

The builder does not delete existing channels. It adds missing categories, channels, and roles.

## Optional AI organizer

Add an OpenAI API key to `.env`:

```env
OPENAI_API_KEY=your_key_here
AI_MODEL=gpt-4.1-mini
```

Then restart the bot and use `/ask_organizer`.
API use may incur charges on the OpenAI account associated with the key.

## Store / services layout

Run `/build_server` and choose **Store / services server**.

This creates an About Us section with locked member/vouch counters, an Information section with rules, announcements, updates, and restocks, plus Community, Support, and private Staff sections.

Run `/update_stats` to refresh the counters.

## Complete combined layout

The Store / services template includes all requested sections and channels:

- About Us counters
- Information: rules, announcements, updates, restocks
- Support: support-ticket, faq, open-a-ticket
- Chat: general, general-support, bot-commands, clips, dma-chat, reviews, configs, ban-reports, recommendations
- Private Staff: staff-chat and mod-logs
