import httpx

async def save_home_html():
    async with httpx.AsyncClient() as client:
        response = await client.get("https://4r.2qk9x7b.shop/")
        if response.status_code == 200:
            with open("anime_home.html", "w", encoding="utf-8") as f:
                f.write(response.text)
            print("Saved anime home HTML to anime_home.html")
        else:
            print(f"Failed to fetch home HTML: {response.status_code}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(save_home_html())
