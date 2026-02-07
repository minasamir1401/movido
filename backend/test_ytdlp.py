import asyncio
from downloader import downloader

async def test():
    url = "https://youtu.be/RwPQ1w-AwlM?si=fAdURxHzQ0VAvW4s"
    print(f"Fetching info for: {url}")
    info = await downloader.get_info(url)
    if "error" in info:
        print(f"Error: {info['error']}")
    else:
        print(f"Success! Title: {info.get('title')}")
        formats = info.get('formats', [])
        print(f"Formats count: {len(formats)}")
        combined = [f for f in formats if f.get('acodec') != 'none' and f.get('vcodec') != 'none']
        print(f"Combined (audio+video) formats: {len(combined)}")
        for f in combined[:5]:
            print(f" - {f.get('format_id')}: {f.get('ext')} {f.get('format_note')} ({f.get('resolution')})")

if __name__ == "__main__":
    asyncio.run(test())
