# Cloudflare Workers Deployment Guide

This guide will help you deploy the Cloudflare Worker proxy for your Debrid-Link bot.

## Why Use Cloudflare Workers?

**Problem:** When multiple users download from Debrid-Link using different IPs, your account can get flagged or banned for sharing.

**Solution:** Route all downloads through a Cloudflare Worker - all requests to Debrid-Link come from a single IP (Cloudflare's), preventing account bans.

**Benefits:**
- ✅ **100% Free** - 100,000 requests/day on free tier
- ✅ **Single IP** - All Debrid-Link requests from one source
- ✅ **URL Obfuscation** - Hides actual Debrid-Link URLs from users
- ✅ **No Credit Card Required**

---

## Step 1: Create Cloudflare Account

1. Go to [https://dash.cloudflare.com/sign-up](https://dash.cloudflare.com/sign-up)
2. Sign up with your email (free account, no credit card needed)
3. Verify your email

---

## Step 2: Install Wrangler CLI

Wrangler is Cloudflare's command-line tool for deploying Workers.

### Option A: Using npm (Recommended)

```bash
npm install -g wrangler
```

### Option B: Using yarn

```bash
yarn global add wrangler
```

### Verify Installation

```bash
wrangler --version
```

---

## Step 3: Login to Cloudflare

```bash
wrangler login
```

This will open a browser window. Click "Allow" to authorize Wrangler.

---

## Step 4: Deploy the Worker

Navigate to the cloudflare directory:

```bash
cd /home/rathi/AntiGravity/debrid-bot/cloudflare
```

Deploy the worker:

```bash
wrangler deploy
```

**Important:** Note the URL that's displayed after deployment. It will look like:
```
https://debrid-proxy.<your-subdomain>.workers.dev
```

---

## Step 5: Update Bot Configuration

1. Open your `.env` file:

```bash
nano /home/rathi/AntiGravity/debrid-bot/.env
```

2. Add the `WORKER_URL` variable with your worker URL:

```env
API_ID=your_api_id
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
DEBRID_KEY=your_debrid_key
ADMIN_IDS=your_admin_ids
WORKER_URL=https://debrid-proxy.<your-subdomain>.workers.dev
```

3. Save and exit (Ctrl+X, then Y, then Enter)

---

## Step 6: Install New Dependency

The bot now uses the `cryptography` library:

```bash
cd /home/rathi/AntiGravity/debrid-bot
pip install -r requirements.txt
```

Or install just the new dependency:

```bash
pip install cryptography
```

---

## Step 7: Restart the Bot

Restart your bot to apply the changes:

```bash
# If running directly
python bot.py

# If using systemd service
sudo systemctl restart debrid-bot

# If on Render/other hosting
# Just push the changes, it will auto-redeploy
```

---

## Step 8: Test the Setup

1. Send a test link to your bot:
   ```
   /dl https://example.com/test-file.zip
   ```

2. Check the download button URL:
   - It should start with your worker URL: `https://debrid-proxy.*.workers.dev/download?data=...`
   - It should NOT be the direct Debrid-Link URL

3. Click the download button and verify the file downloads correctly

---

## Verification Checklist

- [ ] Cloudflare account created
- [ ] Wrangler CLI installed and logged in
- [ ] Worker deployed successfully
- [ ] `WORKER_URL` added to `.env`
- [ ] `cryptography` installed
- [ ] Bot restarted
- [ ] Download URLs now use worker domain
- [ ] Files download successfully through worker

---

## Troubleshooting

### Worker deployment fails

```bash
# Make sure you're in the correct directory
cd /home/rathi/AntiGravity/debrid-bot/cloudflare

# Check wrangler.toml exists
ls -la

# Try deploying again
wrangler deploy
```

### Downloads don't use worker URL

1. Check `.env` has `WORKER_URL` set correctly
2. Restart the bot
3. Verify the URL is loaded:
   ```python
   python -c "from config import config; print(config.WORKER_URL)"
   ```

### Worker returns errors

Check the worker logs:

```bash
wrangler tail
```

Then trigger a download and watch the logs in real-time.

### "Invalid data parameter" error

This means URL encoding failed. Check:
1. The `data` parameter in the URL
2. Worker logs for decoding errors

---

## Advanced: Monitoring Usage

Check your worker's usage stats:

```bash
wrangler metrics
```

Or visit: [https://dash.cloudflare.com](https://dash.cloudflare.com) → Workers & Pages → debrid-proxy → Metrics

---

## Optional: Custom Domain

Want a custom domain like `download.yourdomain.com` instead of `workers.dev`?

1. Add your domain to Cloudflare (requires DNS management)
2. In `wrangler.toml`, add:
   ```toml
   routes = [
     { pattern = "download.yourdomain.com/*", zone_name = "yourdomain.com" }
   ]
   ```
3. Deploy again: `wrangler deploy`

**Note:** This requires the Workers Paid plan ($5/month).

---

## Cost Breakdown

| Tier | Requests/Day | Cost |
|------|--------------|------|
| **Free** | 100,000 | $0 |
| Paid | Unlimited | $5/month |

For most users, the **free tier is more than enough**!

---

## Security Note

The current implementation uses **base64 encoding** (not encryption) for URL obfuscation. This is sufficient for preventing casual URL sharing.

For production with sensitive data, consider implementing proper encryption using the `ENCRYPTION_KEY` mechanism (already supported in the code but not enabled).

---

## Need Help?

- **Cloudflare Docs:** [https://developers.cloudflare.com/workers](https://developers.cloudflare.com/workers)
- **Wrangler Docs:** [https://developers.cloudflare.com/workers/wrangler](https://developers.cloudflare.com/workers/wrangler)
- **Bot Issues:** Check `bot.log` for error messages

Enjoy your IP-safe downloads! 🚀
