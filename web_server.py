"""Simple health check web server for keeping the bot alive on Render."""
from aiohttp import web
import asyncio
import os
import html
import logging
from urllib.parse import unquote

logger = logging.getLogger(__name__)


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


async def file_list_view(request):
    """Display file list for a torrent."""
    from services.file_list_service import get_file_list
    from utils.url_proxy import encode_url
    from utils.display import human_readable_size
    
    file_list_id = request.match_info.get('id', '')
    
    if not file_list_id:
        return web.Response(
            text="<h1>Error: Invalid file list ID</h1>",
            content_type='text/html',
            status=400
        )
    
    # Get file list from database
    file_list_data = await get_file_list(file_list_id)
    
    if not file_list_data:
        error_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>File List Not Found</title>
            <style>
                body {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    padding: 20px;
                }
                .container {
                    text-align: center;
                    background: rgba(255, 255, 255, 0.1);
                    border-radius: 20px;
                    backdrop-filter: blur(10px);
                    padding: 40px;
                    box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
                }
                .error-icon { font-size: 4em; margin-bottom: 20px; }
                h1 { font-size: 2em; margin-bottom: 20px; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="error-icon">❌</div>
                <h1>File List Not Found</h1>
                <p>This file list has expired or does not exist.</p>
            </div>
        </body>
        </html>
        """
        return web.Response(text=error_html, content_type='text/html', status=404)
    
    # Build HTML for files
    torrent_name = file_list_data['torrent_name']
    files = file_list_data['files']
    
    # Build HTML for each file
    file_items_html = ""
    video_extensions = {'.mkv', '.mp4', '.avi', '.mov', '.flv', '.wmv', '.webm', '.m4v', '.mpg', '.mpeg'}
    
    for file_obj in files:
        # Ensure downloadUrl exists, otherwise skip
        if 'downloadUrl' not in file_obj:
            continue
            
        file_name = html.escape(file_obj.get('name', 'Unknown'))
        file_size = file_obj.get('size', 0)
        download_url = file_obj.get('downloadUrl', '')  # Don't escape - breaks the URL!
        
        # Determine file icon based on extension
        ext = os.path.splitext(file_name)[1].lower()
        icon = '🎬' if ext in video_extensions else '📄'
        
        # Format file size
        size_str = human_readable_size(file_size)
        
        # Check if it's a video file for stream button
        is_video = ext in video_extensions
        stream_button = ""
        if is_video:
            # Use Cloudflare Worker proxified URL for better reliability
            proxied_url = encode_url(download_url, file_obj.get('name', 'Video'))
            # Create stream URL with the proxified URL
            from urllib.parse import quote
            stream_url = f"/stream?url={quote(proxied_url)}&name={quote(file_obj.get('name', 'Video'))}"
            stream_button = f'''
                    <a href="{html.escape(stream_url)}" class="btn btn-stream" target="_blank">
                        🎥 Stream
                    </a>'''
        
        file_items_html += f'''
            <div class="file-item">
                <div class="file-info">
                    <div class="file-name">
                        <span class="file-icon">{icon}</span>
                        <span>{file_name}</span>
                    </div>
                    <div class="file-size">{size_str}</div>
                </div>
                <div class="file-actions">
                    <button class="btn btn-copy" onclick="copyLink('{download_url}', this)">
                        📋 Copy Link
                    </button>{stream_button}
                    <a href="{download_url}" class="btn btn-download" download>
                        ⬇️ Download
                    </a>
                </div>
            </div>'''

        
    # Read template
    template_path = os.path.join(os.path.dirname(__file__), 'templates', 'file_list.html')
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template = f.read()
    except FileNotFoundError:
        logger.error("file_list.html template not found")
        return web.Response(
            text="<h1>Error: Template not found</h1>",
            content_type='text/html',
            status=500
        )
    
    # Replace placeholders (simple template - no mustache needed)
    torrent_name_escaped = torrent_name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    rendered_html = template.replace('{{torrent_name}}', torrent_name_escaped)
    rendered_html = rendered_html.replace('{{file_count}}', str(len(files)))
    
    # Since we're not using a template engine, we'll replace the {{#files}} section
    # Find and replace the files loop section
    import re
    files_section_pattern = r'{{#files}}.*?{{/files}}'
    rendered_html = re.sub(files_section_pattern, file_items_html, rendered_html, flags=re.DOTALL)
    
    return web.Response(text=rendered_html, content_type='text/html')


async def cleanup_task(app):
    """Background task to cleanup old file list entries."""
    from services.file_list_service import cleanup_old_entries
    from config import settings
    
    logger.info("File list cleanup task started")
    
    while True:
        try:
            await asyncio.sleep(settings.FILE_LIST_CLEANUP_INTERVAL)
            deleted_count = await cleanup_old_entries()
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} expired file list entries")
        except Exception as e:
            logger.error(f"Error in cleanup task: {e}", exc_info=True)


async def start_web_server():
    """Start the health check web server."""
    app = web.Application()
    app.router.add_get('/', health_check)
    app.router.add_get('/health', health_check)
    app.router.add_get('/stream', stream_player)  # Streaming endpoint
    app.router.add_get('/files/{id}', file_list_view)  # File list viewer
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Use PORT from environment variable or default to 8080
    port = int(os.environ.get('PORT', 8080))
    
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    # Start cleanup background task
    asyncio.create_task(cleanup_task(app))
    
    print(f"✓ Health check server running on port {port}")
    print(f"✓ Stream player available at http://localhost:{port}/stream")
    print(f"✓ File list viewer available at http://localhost:{port}/files/<id>")
    return runner

