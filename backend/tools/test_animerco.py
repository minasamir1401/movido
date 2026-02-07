
import requests
from bs4 import BeautifulSoup

url = "https://ww1.animerco.org/episodes/one-punch-man-%d8%a7%d9%84%d8%ad%d9%84%d9%82%d8%a9-1/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

resp = requests.get(url, headers=headers)
soup = BeautifulSoup(resp.text, 'html.parser')

print("--- Player Options ---")
opts = soup.select('.player-option, .server-list a, .watch-servers a, a[data-post]')
for opt in opts:
    print(f"Tag: {opt.name}, Text: {opt.get_text(strip=True)}, Attrs: {opt.attrs}")

print("\n--- Download Links ---")
dls = soup.select('a[href*="/links/"], a[href*="download"], .download-link')
for dl in dls:
    print(f"Text: {dl.get_text(strip=True)}, Href: {dl.get('href')}")

print("\n--- Episode List ---")
eps = soup.select('.episodes-list a, .anime-episodes a, a[href*="/episodes/"]')
for ep in eps[:10]:
    print(f"Text: {ep.get_text(strip=True)}, Href: {ep.get('href')}")
