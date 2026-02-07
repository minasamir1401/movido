import httpx
import json

async def test_anime_home():
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8000/anime/home")
        if response.status_code == 200:
            data = response.json()
            with open("anime_home_debug.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            print("Successfully saved anime home data to anime_home_debug.json")
            
            # Check for posters
            for section, items in data.items():
                print(f"Section: {section}")
                if items:
                    print(f"  First item poster: {items[0].get('poster')}")
        else:
            print(f"Failed to fetch anime home: {response.status_code}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_anime_home())
