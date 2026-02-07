import httpx
from bs4 import BeautifulSoup
import re

url = "https://larooza.bond/video.php?vid=012bf4d43"
headers = {"User-Agent": "Mozilla/5.0"}

resp = httpx.get(url, headers=headers, timeout=20, follow_redirects=True)
soup = BeautifulSoup(resp.text, 'html.parser')

# Find the main title
h1 = soup.find('h1')
title = h1.get_text().strip() if h1 else ""
print(f"Title: {title}")

# Extract series name (remove episode info)
series_name = re.sub(r'الحلقة.*', '', title).strip()
print(f"Series: {series_name}")

# Find all links with this series name
print("\n--- Links containing series name ---")
for a in soup.find_all('a', href=True):
    text = a.get_text().strip()
    if series_name in text and 'حلقة' in text:
        href = a.get('href')
        # Check parent structure
        parent_class = a.parent.get('class') if a.parent else None
        print(f"{text[:50]} -> {href}")
        print(f"  Parent: {parent_class}")
