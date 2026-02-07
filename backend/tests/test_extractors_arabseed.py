import asyncio
import sys
import os

# Add the backend and scraper directories to the path
sys.path.append(os.path.abspath(os.path.join(os.getcwd())))
sys.path.append(os.path.abspath(os.path.join(os.getcwd(), 'backend')))

from backend.scraper.extractors.engine import ExtractorEngine

async def test_extractors():
    urls = [
        "https://m.reviewrate.net/embed-zkkedwhvh4op.html",
        "https://savefiles.com/e/g7nmj0m2q1ns",
        "https://up4fun.top/embed-8bpbbkp8azzy.html",
        "https://vidmoly.net/embed-v5y1yxiz1l85.html",
        "https://voe.sx/e/vwujeidzydg5",
        "https://bysezejataos.com/e/1wnmflyd24e0"
    ]
    
    print(f"Testing {len(urls)} URLs from ArabSeed...\n")
    
    for url in urls:
        print(f"Testing: {url}")
        try:
            result = await ExtractorEngine.extract(url)
            if result:
                print(f"  ✅ SUCCESS: {result['type']} -> {result['url'][:100]}...")
            else:
                print(f"  ❌ FAILED to extract.")
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
        print("-" * 30)

if __name__ == "__main__":
    asyncio.run(test_extractors())
