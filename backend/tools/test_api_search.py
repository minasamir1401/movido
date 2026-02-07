import httpx
import asyncio

async def test_api_search():
    query = "Darwin Jihen"
    print(f"Testing API search for: {query}")
    async with httpx.AsyncClient() as client:
        # Note: Adjust port if needed, assuming 8000
        response = await client.get(f"http://localhost:8000/api/movies/search?q={query}")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Results found: {len(data)}")
            for item in data:
                print(f"- {item['title']} (Type: {item['type']})")
        else:
            print(f"Response: {response.text}")

if __name__ == "__main__":
    asyncio.run(test_api_search())
