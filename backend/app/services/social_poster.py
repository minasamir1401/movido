import logging
import httpx
from ..core.config import settings

logger = logging.getLogger("social_poster")

class SocialPoster:
    async def post_new_content(self, title: str, url: str, poster_url: str):
        if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHANNEL_ID:
            # Silent return if no credentials, avoiding spam logs if intentional
            return

        message = f"🎬 **New Release**\n\n**{title}**\n\nWatch now: {url}"
        
        api_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendPhoto"
        
        payload = {
            "chat_id": settings.TELEGRAM_CHANNEL_ID,
            "photo": poster_url,
            "caption": message,
            "parse_mode": "Markdown"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(api_url, json=payload, timeout=10.0)
                if resp.status_code != 200:
                    # Fallback to text message if photo fails or invalid
                    await self._send_text_message(message)
                else:
                    logger.info(f"Successfully posted '{title}' to Telegram.")
        except Exception as e:
            logger.error(f"Error posting to Telegram: {e}")
            
    async def _send_text_message(self, message: str):
        api_url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": settings.TELEGRAM_CHANNEL_ID,
            "text": message,
            "parse_mode": "Markdown"
        }
        try:
            async with httpx.AsyncClient() as client:
                await client.post(api_url, json=payload, timeout=10.0)
        except Exception as e:
            logger.error(f"Error sending text fallback: {e}")

social_poster = SocialPoster()
