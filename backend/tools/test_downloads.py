from bs4 import BeautifulSoup
import re

html = open("c:\\Users\\Mina\\Desktop\\lmina\\backend\\tools\\ep.html", "r", encoding="utf-8").read()
soup = BeautifulSoup(html, 'html.parser')

def _extract_downloads(soup):
    links = []
    # Animerco usually has a #download table
    # Check for table rows
    rows = soup.select('#download table tbody tr')
    for row in rows:
        # Columns: Link | Server | Quality | Language
        cols = row.find_all('td')
        if len(cols) >= 2:
            link_node = cols[0].find('a')
            if not link_node: continue
            
            url = link_node.get('href')
            
            # Extract server name from the second column (icon or text)
            server_node = cols[1]
            server_name = server_node.get_text(strip=True)
            if not server_name:
                # Try image alt or data-src domain
                img = server_node.find('img') or server_node.find('div', class_='favicon')
                if img:
                    src = img.get('data-src') or img.get('src') or ""
                    if 'googleusercontent' in src and 'domain=' in src:
                        server_name = src.split('domain=')[1].split('&')[0]
                    elif 'favicons' in src:
                        server_name = "Server" # Generic
            
            # Extract Quality
            quality = ""
            if len(cols) > 2:
                quality = cols[2].get_text(strip=True)
                
            links.append({
                "server": server_name or "Download",
                "url": url,
                "quality": quality
            })
    return links

dls = _extract_downloads(soup)
print(f"Found {len(dls)} download links.")
for d in dls:
    print(d)

# Test conversion logic
servers = []
seen_urls = set()
for dl in dls:
    url = dl.get('url', '')
    final_url = url # Simulating redirect resolution failure or if direct
    stream_url = None
    name = dl.get('server', 'Server')
    
    # Mocking what the redirect might point to based on the favicon domain
    if 'mp4upload' in name:
        final_url = "https://www.mp4upload.com/0p806ivodn"
        stream_url = "https://www.mp4upload.com/embed-0p806ivodn.html"
    elif 'mega' in name:
        final_url = "https://mega.nz/file/..."
        stream_url = final_url.replace('/file/', '/embed/')
        
    if stream_url:
        print(f"Converted {name} to {stream_url}")
        servers.append({"name": name, "url": stream_url, "type": "iframe"})

print(f"Generated {len(servers)} fallback servers.")
