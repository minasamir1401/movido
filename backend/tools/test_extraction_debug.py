import asyncio
import base64
import json
import os
import sys

# Add backend directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper.engine import scraper

async def test_extraction():
    safe_id = "aHR0cHM6Ly9sYXJvb3phLmJvbmQvdmlkZW8ucGhwP3ZpZD0zYzZlNThkNWE="
    print(f"Testing extraction for ID: {safe_id}")
    try:
        details = await scraper.fetch_details(safe_id)
        # Only print title and servers to avoid truncation
        result = {
            "title": details.get("title"),
            "servers": details.get("servers"),
            "download_links": details.get("download_links")
        }
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error during extraction: {e}")

if __name__ == "__main__":
    asyncio.run(test_extraction())
