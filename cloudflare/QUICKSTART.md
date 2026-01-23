# Quick Start - Cloudflare Workers Proxy

## What Is This?

A proxy layer that routes all Debrid-Link downloads through Cloudflare Workers, preventing account bans from multiple user IPs.

## Should I Use It?

**Use if:**
- ✅ You're running a public bot (multiple users)
- ✅ Users download from different locations/IPs
- ✅ You want to prevent account sharing detection

**Skip if:**
- ❌ Personal use only (single user)
- ❌ Trusted friends/family only
- ❌ Already using other IP protection

## 5-Minute Setup

### 1. Install Wrangler
```bash
npm install -g wrangler
```

### 2. Login to Cloudflare
```bash
wrangler login
```
(Creates free account if needed)

### 3. Deploy Worker
```bash
cd /home/rathi/AntiGravity/debrid-bot/cloudflare
wrangler deploy
```

Note the URL shown (e.g., `https://debrid-proxy.*.workers.dev`)

### 4. Update Config
```bash
nano /home/rathi/AntiGravity/debrid-bot/.env
```

Add this line:
```env
WORKER_URL=https://debrid-proxy.your-subdomain.workers.dev
```

### 5. Install Dependency
```bash
pip install cryptography
```

### 6. Restart Bot
```bash
python /home/rathi/AntiGravity/debrid-bot/bot.py
```

## Verify It's Working

1. Send download command: `/dl <any-link>`
2. Check download button URL
3. Should start with: `https://debrid-proxy.*.workers.dev`
4. NOT: `https://debrid-link.fr` or direct URL

## Cost

**$0.00** - Completely free (100,000 requests/day)

## Full Documentation

See: [`cloudflare/README.md`](file:///home/rathi/AntiGravity/debrid-bot/cloudflare/README.md)

## Troubleshooting

**Deployment fails?**
```bash
npm install -g wrangler
wrangler login
cd /home/rathi/AntiGravity/debrid-bot/cloudflare
wrangler deploy
```

**URLs still direct?**
- Check `.env` has `WORKER_URL` set
- Restart bot
- Clear Telegram cache (settings > data > clear cache)

**Worker errors?**
```bash
wrangler tail
```
Watch logs while triggering download

## Disable Proxy

Remove `WORKER_URL` from `.env` and restart bot.
