from scraper.anime4up import anime4up_scraper
import asyncio

async def debug_home_html():
    html = await anime4up_scraper._get_html(anime4up_scraper.source_url)
    if html:
        with open("anime_home_scraper.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("Saved anime home HTML using scraper to anime_home_scraper.html")

if __name__ == "__main__":
    asyncio.run(debug_home_html())
