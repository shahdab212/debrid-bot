"""File link generation and management."""

import os
from typing import List, Dict, Any


def get_file_links(files: List[Dict[str, Any]]) -> str:
    """Generates formatted links for files, distinguishing streams."""
    from utils.url_proxy import encode_url
    
    links_text = ""
    if not files:
        return links_text
    
    links_text = "\n\n📂 **Files:**"
    VIDEO_EXTS = {'.mkv', '.mp4', '.avi', '.mov', '.flv', '.wmv'}
    
    count = 0
    for f in files:
        if count >= 20:  # Increased limit to 20 files
            links_text += f"\n...and {len(files)-20} more."
            break
            
        if "downloadUrl" in f:
            name = f['name']
            ext = os.path.splitext(name)[1].lower()
            
            # Proxify the URL for embedded link
            proxied_url = encode_url(f['downloadUrl'], name)
            
            if ext in VIDEO_EXTS:
                # Video file with proxified link
                links_text += f"\n- 🎬 [{name}]({proxied_url})"
            else:
                # Other files with proxified link
                links_text += f"\n- ⬇️ [{name}]({proxied_url})"
        count += 1
    return links_text
