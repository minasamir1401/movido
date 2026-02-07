import yt_dlp
import asyncio
from functools import partial

class Downloader:
    def __init__(self):
        self.default_opts = {
            'quiet': True,
            'no_warnings': True,
            'format': 'best',
            'extract_flat': True, # Faster for playlists, maybe remove for single video details
        }

    async def get_info(self, url: str):
        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(None, self._fetch_info, url)
        except Exception as e:
            return {"error": str(e)}

    def _fetch_info(self, url: str):
        # We might want full info so extract_flat might be bad if we need formats.
        # But for 'get_info' often we just need metadata.
        # Let's use default options without extract_flat for now to be safe with direct video links.
        opts = {
            'quiet': True, 
            'no_warnings': True,
            'format': 'best'
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)

downloader = Downloader()
