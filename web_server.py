"""Simple health check web server for keeping the bot alive on Render."""
from aiohttp import web
import asyncio
import os
from urllib.parse import unquote

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


async def stream_player(request):
    """Serve video player with Shaka Player for streaming."""
    # Get the proxified video URL from query params
    video_url = request.query.get('url', '')
    filename = request.query.get('name', 'Video')
    
    if not video_url:
        return web.Response(
            text="<h1>Error: No video URL provided</h1><p>Please provide a 'url' parameter.</p>",
            content_type='text/html',
            status=400
        )
    
    # Decode filename if needed
    filename = unquote(filename)
    
    # Read the HTML template
    template_path = os.path.join(os.path.dirname(__file__), 'templates', 'player.html')
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()
        
        # Replace placeholders
        html = template.replace('{{video_url}}', video_url)
        html = html.replace('{{filename}}', filename)
        
        return web.Response(text=html, content_type='text/html')
    
    except FileNotFoundError:
        return web.Response(
            text="<h1>Error: Player template not found</h1>",
            content_type='text/html',
            status=500
        )
    except Exception as e:
        return web.Response(
            text=f"<h1>Error loading player</h1><p>{str(e)}</p>",
            content_type='text/html',
            status=500
        )


async def start_web_server():
    """Start the health check web server."""
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    app.router.add_get('/stream', stream_player)  # New streaming endpoint
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Use PORT from environment variable or default to 8080
    port = int(os.environ.get('PORT', 8080))
    
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    print(f"✓ Health check server running on port {port}")
    print(f"✓ Stream player available at http://localhost:{port}/stream")
    return runner
