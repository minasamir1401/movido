import asyncio
from scraper.anime4up import anime4up_scraper

async def test_search():
    query = "Darwin Jihen"
    print(f"Searching for: {query}")
    results = await anime4up_scraper.search(query)
    print(f"Results found: {len(results)}")
    for item in results:
        print(f"- {item['title']} (ID: {item['id']})")

if __name__ == "__main__":
    asyncio.run(test_search())
