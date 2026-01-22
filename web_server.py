"""Simple health check web server for keeping the bot alive on Render."""
from aiohttp import web
import asyncio

async def health_check(request):
    """Simple health check endpoint."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Debrid-Link Bot</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
            }
            .container {
                text-align: center;
                padding: 40px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 20px;
                backdrop-filter: blur(10px);
                box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
            }
            h1 {
                margin: 0 0 20px 0;
                font-size: 3em;
            }
            .status {
                display: inline-block;
                padding: 10px 30px;
                background: #4CAF50;
                border-radius: 50px;
                font-weight: bold;
                margin-top: 20px;
                animation: pulse 2s infinite;
            }
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.7; }
            }
            .emoji {
                font-size: 4em;
                margin-bottom: 20px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="emoji">🤖</div>
            <h1>Debrid-Link Bot</h1>
            <p>Telegram bot for downloading via Debrid-Link</p>
            <div class="status">✓ Bot is Running</div>
        </div>
    </body>
    </html>
    """
    return web.Response(text=html, content_type='text/html')

async def start_web_server():
    """Start the health check web server."""
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Use PORT from environment variable or default to 8080
    import os
    port = int(os.environ.get('PORT', 8080))
    
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    print(f"✓ Health check server running on port {port}")
    return runner
