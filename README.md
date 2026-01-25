# Debrid-Link Telegram Bot

A production-grade Telegram bot for downloading torrents, magnet links, and hoster links using Debrid-Link.fr service.

## ✨ Features

### Core Functionality
- 🧲 **Multi-format Support**: Magnet links, torrent files (file/URL), and 50+ file hosters
- 📦 **Smart ZIP**: Auto-creates ZIP for torrents with 15+ files
- 🎯 **Flexible ZIP**:
  - Add `-zip` or `-z` to force ZIP creation
  - Add `-nozip` or `-nz` to disable auto-ZIP (download files individually)
- 📊 **Real-time Progress**: Live download progress with speed and ETA
- 🔗 **Direct Download Links**: Ready-to-use Debrid-Link CDN URLs
- 🛡️ **Cloudflare Proxy**: Route downloads through Cloudflare Workers (prevents IP bans)

### New Features (v2.0)
- ⚙️ **Pydantic Configuration**: Type-safe settings with validation
- ✅ **Input Validators**: Comprehensive validation for all input types
- 🔄 **Auto-Retry Logic**: Exponential backoff for failed API calls
- 📈 **Download History**: Track all downloads with full details
- 📊 **Metrics Collection**: Analytics and usage tracking
- 📉 **Statistics Dashboard**: Beautiful `/stats` command for admins

### User Experience
- 🎨 **Beautiful UI**: Aesthetic messages with bold/italic styling
- ⬇️ **Smart Buttons**: Download buttons for all file types
- 👤 **User Mentions**: Clickable user profiles in messages
- 💬 **Clear Help System**: Separate user and admin commands
- 📂 **Folder Detection**: Blocks MEGA/GDrive folder links with helpful messages
- 🌐 **Torrent URL Support**: Direct download from http/https links pointing to .torrent files

### Administration
- 🔐 **Persistent Auth**: Database-backed authorization system (PostgreSQL/SQLite)
- 👥 **Multi-admin Support**: Multiple bot administrators
- 📋 **Admin Logging**: View bot logs with `/log` command
- 📊 **Account Limits**: Check Debrid-Link usage with `/limits`
- 📈 **Bot Statistics**: View download stats, success rates with `/stats`
- 🔄 **Remote Management**: Restart the bot remotely with `/restart`
- 👥 **User Management**: List all authorized users with `/users`

### Deployment
- 🚀 **Render Support**: Built-in health check endpoint
- 🐳 **Docker Ready**: Full Docker & Docker Compose support
- 🌐 **Always Online**: Health check page for uptime monitoring
  - **Single IP Protection**: Optional Cloudflare Worker proxy

## 🚀 Quick Start

### Deploy to Render

1. Fork this repository
2. Create a new Web Service on [Render](https://render.com)
3. Connect your forked repository
4. Add environment variables (see Configuration)
5. Set Start Command: `python bot.py`
6. Deploy!

The bot includes a health check endpoint at `/` and `/health` for Render's uptime monitoring.

### Docker Deployment

```bash
# Clone repository
git clone <your-repo-url>
cd debrid-bot

# Create .env file (see Configuration)

# Start with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f
```

### Manual Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file (see Configuration)

# Run bot
python bot.py
```

## ⚙️ Configuration

Create a `.env` file with the following variables:

```env
API_ID=your_telegram_api_id
API_HASH=your_telegram_api_hash
BOT_TOKEN=your_bot_token_from_botfather
DEBRID_KEY=your_debrid_link_api_key
ADMIN_IDS=your_telegram_id,another_admin_id
PORT=8080  # Optional, for health check server
WORKER_URL=https://your-worker.workers.dev  # Optional, for Cloudflare proxy
DATABASE_URL=postgresql://user:pass@host:5432/dbname  # Optional, defaults to SQLite
```

### Database Configuration

The bot uses a database to store authorized chat IDs, ensuring they persist across deployments.

**Local Development:**
- Uses SQLite by default (stored in `./data/bot.db`)
- No configuration needed
- Perfect for testing

**Production on Render:**
- **Recommended**: Use PostgreSQL for true persistence
- Add PostgreSQL addon to your Render service
- Render automatically sets `DATABASE_URL`
- Authorized chats survive all deployments

## 📱 Commands

### User Commands

**Download Commands:**
- `/dl <link>` - Download any supported link
- `/dl <link> -zip` - Download and create ZIP archive
- `/dl <link> -nozip` - Download without creating ZIP (overrides auto-ZIP)
- `/dl -z` - Reply to a link/file to download with ZIP
- `/dl -nz` - Reply to a link/file to download without ZIP

**Info Commands:**
- `/start` - Welcome message and quick start guide
- `/help` - Comprehensive help with all commands

### Admin Commands

- `/auth [chat_id]` - Authorize a chat (uses current chat if no ID given)
- `/deauth [chat_id]` - Revoke chat authorization
- `/users` - List all authorized users/chats
- `/stats` - View bot statistics (downloads, success rates, data transferred)
- `/limits` - View Debrid-Link account usage and limits
- `/log [lines]` - View recent bot logs (default: 60 lines)
- `/restart` - Restart the bot process
- `/cancel` - Cancel an active download (Reply to download message)

## 🎯 Usage Examples

### Download a Magnet Link
```
/dl magnet:?xt=urn:btih:abc123...
```

### Download with ZIP Archive
```
/dl magnet:?xt=urn:btih:abc123... -zip
```

### Download Large Torrent without ZIP
```
/dl magnet:?xt=urn:btih:abc123... -nozip
```
*(Useful for torrents with >15 files where you want individual links)*

### Reply to Download
1. Send or forward a magnet link, torrent file, or hoster link
2. Reply to it with: `/dl` or `/dl -z` (ZIP) or `/dl -nz` (No ZIP)

## 🔗 Supported Sources

### Torrents
- 🧲 Magnet links
- 📁 .torrent files (upload or forward)
- 🌐 .torrent URLs (direct HTTP/HTTPS links)

### File Hosters (50+)
- MEGA (file links only, not folders)
- RapidGator
- Uploaded.to
- 1fichier
- Mediafire
- And many more...

**Note:** Folder links (MEGA, Google Drive) are automatically detected and rejected with helpful instructions.

## 🛡️ Cloudflare Workers Proxy (Optional)

### Why Use It?

**Problem:** When multiple users download files using different IPs, Debrid-Link may flag or ban your account for sharing.

**Solution:** Route all downloads through a Cloudflare Worker - ensuring all requests come from a single IP.

### Benefits

- ✅ **100% Free** - 100,000 requests/day on free tier
- ✅ **No Credit Card** - Free tier requires no payment info
- ✅ **IP Protection** - All Debrid-Link requests from one source
- ✅ **URL Obfuscation** - Hides actual Debrid-Link URLs from users
- ✅ **Easy Setup** - 5-minute deployment

### Quick Setup

1. **Create Cloudflare Account** (free)
   ```bash
   # Visit: https://dash.cloudflare.com/sign-up
   ```

2. **Install Wrangler CLI**
   ```bash
   npm install -g wrangler
   wrangler login
   ```

3. **Deploy Worker**
   ```bash
   cd cloudflare
   wrangler deploy
   ```

4. **Update Config**
   Add your worker URL to `.env`:
   ```env
   WORKER_URL=https://debrid-proxy.your-subdomain.workers.dev
   ```

5. **Restart Bot**
   ```bash
   python bot.py
   ```

### Testing

After setup, download links will:
- Start with your worker domain (not Debrid-Link)
- Route through Cloudflare's network
- Show as single IP to Debrid-Link

**Full deployment guide:** See [`cloudflare/README.md`](cloudflare/README.md)

## 🏗️ Project Structure

```
debrid-bot/
├── bot.py                   # Main bot application (117 lines - modular!)
├── web_server.py            # Health check server (Render support)
├── start.sh                 # Convenience start script
├── models.py                # Database models (AuthorizedChat, DownloadHistory, Metrics)
├── database.py              # Database connection manager
├── requirements.txt         # Python dependencies
├── Dockerfile              # Docker image
├── docker-compose.yml      # Docker Compose config
├── data/                   # SQLite database storage (gitignored)
├── config/
│   ├── __init__.py        # Config package
│   └── settings.py        # Pydantic settings with validation
├── core/                   # Core business logic
│   ├── __init__.py
│   ├── torrent_manager.py # Torrent tracking & monitoring
│   ├── message_builder.py # Message formatting & updates
│   └── file_manager.py    # File link generation
├── handlers/               # Command handlers
│   ├── __init__.py
│   ├── user_commands.py   # /start, /help, /dl
│   ├── admin_commands.py  # /auth, /stats, /cancel, etc.
│   └── callback_handlers.py # Inline button callbacks
├── services/
│   ├── auth_service.py    # Authorization system (database-backed)
│   ├── debrid_service.py  # Debrid-Link API client
│   ├── paste_service.py   # Paste service for long outputs
│   ├── history_service.py # Download history tracking
│   └── metrics_service.py # Metrics collection & analytics
├── utils/
│   ├── display.py         # Message formatting
│   ├── keyboards.py       # Telegram keyboards
│   ├── url_proxy.py       # URL encoding for Cloudflare proxy
│   ├── validators.py      # Input validation utilities
│   └── retry.py          # Retry logic with exponential backoff
└── cloudflare/             # Cloudflare Workers proxy
    ├── worker.js          # Worker script
    ├── wrangler.toml      # Worker configuration
    └── README.md          # Deployment guide
```

### Code Organization Benefits

- **Modular Design**: Clean separation of concerns
- **Maintainable**: Easy to find and update specific functionality
- **Testable**: Each module can be tested independently
- **Scalable**: Simple to add new features without bloating main file
- **91.8% Smaller**: Main `bot.py` reduced from 1,422 to 117 lines!

## 🐛 Troubleshooting

### Bot Not Responding
- Check logs: `docker-compose logs -f`
- Verify `.env` configuration
- Ensure bot is authorized for the chat: `/auth`

### API Errors
- Verify Debrid-Link API key is valid
- Check account status at debrid-link.fr
- Ensure you have available download slots

### MEGA/Google Drive Issues
- **Folder links are not supported** - use direct file links
- Make sure Google Drive files are publicly accessible
- MEGA folder links: Extract individual file links instead

## 🌐 Health Check Endpoint

The bot runs a web server on port `8080` (configurable via `PORT` env var) with a beautiful status page at:
- `/` - Main status page
- `/health` - Health check endpoint

Perfect for:
- Render.com uptime monitoring
- External ping services (UptimeRobot, etc.)
- Keeping free-tier services always online

## 📄 License

MIT License - Feel free to use and modify!

## 🙏 Support

For issues or questions:
- Use `/help` in the bot
- Check error messages for troubleshooting
- Review this README

---

**Requirements**: Active Debrid-Link premium account

**Powered by**: [Pyrogram](https://docs.pyrogram.org/) & [Debrid-Link](https://debrid-link.fr/)
