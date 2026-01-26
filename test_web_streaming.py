#!/usr/bin/env python3
"""Test script for web streaming functionality."""

import sys
import os
import asyncio

# Set up event loop before any async imports (required for Pyrogram)
try:
    loop = asyncio.get_event_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.url_proxy import encode_url
from utils.web_stream import get_stream_url


def test_url_encoding():
    """Test CF Worker URL encoding."""
    print("🧪 Testing URL Encoding...")
    
    test_url = "https://debrid-link.fr/download/abc123/test-video.mp4"
    test_filename = "test-video.mp4"
    
    proxied = encode_url(test_url, test_filename)
    print(f"  ✓ Original: {test_url}")
    print(f"  ✓ Proxified: {proxied}")
    
    return proxied


def test_stream_url_generation(proxied_url):
    """Test stream URL generation."""
    print("\n🧪 Testing Stream URL Generation...")
    
    test_filename = "test-video.mp4"
    stream_url = get_stream_url(proxied_url, test_filename)
    
    print(f"  ✓ Stream URL: {stream_url}")
    
    # Verify URL structure
    assert "/stream?" in stream_url, "Stream URL should contain /stream endpoint"
    assert "url=" in stream_url, "Stream URL should contain url parameter"
    assert "name=" in stream_url, "Stream URL should contain name parameter"
    
    print("  ✓ URL structure valid")
    return stream_url


def test_keyboard_integration():
    """Test keyboard button integration."""
    print("\n🧪 Testing Keyboard Integration...")
    
    from utils.keyboards import get_file_download_keyboard
    
    test_url = "https://debrid-link.fr/download/xyz789/movie.mp4"
    test_filename = "movie.mp4"
    
    keyboard = get_file_download_keyboard(test_url, test_filename)
    
    assert keyboard is not None, "Keyboard should be generated"
    assert len(keyboard.inline_keyboard) == 2, "Video files should have 2 buttons"
    
    web_stream_button = keyboard.inline_keyboard[0][0]
    download_button = keyboard.inline_keyboard[1][0]
    
    assert "🌐" in web_stream_button.text, "First button should be web stream"
    assert "⬇️" in download_button.text, "Second button should be download"
    assert "/stream?" in web_stream_button.url, "Web stream button should point to /stream"
    
    print(f"  ✓ Web Stream Button: {web_stream_button.text}")
    print(f"  ✓ Download Button: {download_button.text}")
    print("  ✓ Keyboard structure valid")


def test_video_detection():
    """Test video file detection."""
    print("\n🧪 Testing Video File Detection...")
    
    from utils.keyboards import get_file_download_keyboard
    
    # Test video file
    video_keyboard = get_file_download_keyboard("http://example.com/file.mp4", "test.mp4")
    assert len(video_keyboard.inline_keyboard) == 2, "Video should have 2 buttons (stream + download)"
    
    # Test non-video file
    doc_keyboard = get_file_download_keyboard("http://example.com/file.pdf", "test.pdf")
    assert len(doc_keyboard.inline_keyboard) == 1, "Non-video should have 1 button (download only)"
    
    print("  ✓ Video files: 2 buttons (stream + download)")
    print("  ✓ Non-video files: 1 button (download only)")


def main():
    """Run all tests."""
    print("=" * 60)
    print("🎬 Web Streaming Feature Test Suite")
    print("=" * 60)
    
    try:
        # Test 1: URL Encoding
        proxied_url = test_url_encoding()
        
        # Test 2: Stream URL Generation
        stream_url = test_stream_url_generation(proxied_url)
        
        # Test 3: Keyboard Integration
        test_keyboard_integration()
        
        # Test 4: Video Detection
        test_video_detection()
        
        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        print("\n📝 Next Steps:")
        print("  1. Start the bot: python bot.py")
        print("  2. Send a video file/link to the bot")
        print("  3. Look for the '🌐 Web Stream' button")
        print("  4. Click it and verify the player loads")
        print("\n🌐 Stream endpoint will be available at:")
        print("  http://localhost:8080/stream (local)")
        print("  https://your-app.onrender.com/stream (production)")
        
        return 0
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
