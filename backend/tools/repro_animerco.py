import asyncio
import sys
import os
import base64
import re
import httpx
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Robust debug script

async def test():
    url = "https://ww1.animerco.org/episodes/one-punch-man-%d8%a7%d9%84%d8%ad%d9%84%d9%82%d8%a9-1/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": url,
        "X-Requested-With": "XMLHttpRequest"
    }
    
    client = httpx.AsyncClient(headers=headers, verify=False, follow_redirects=True)
    
    print(f"Fetching {url}...")
    resp = await client.get(url)
    print(f"Status: {resp.status_code}")
    
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # Extract servers
    opts = soup.select('a.option[data-post], .server-list a, .watch-servers a, #playeroptionsul li')
    print(f"Found {len(opts)} server options.")
    
    # Extract dtAjax
    dt_ajax = {}
    for s in soup.find_all('script'):
        if s.string and 'var dtAjax' in s.string:
            try:
                # Find start of json
                start = s.string.find('var dtAjax = ') + len('var dtAjax = ')
                end = s.string.find(';', start)
                json_str = s.string[start:end]
                dt_ajax = json.loads(json_str)
                print(f"Extracted dtAjax: {json.dumps(dt_ajax, indent=2)}")
            except Exception as e:
                print(f"Failed to parse dtAjax: {e}")
            break
            
    ajax_url = "https://ww1.animerco.org/wp-admin/admin-ajax.php"
    
    for i, opt in enumerate(opts):
        print(f"\n--- Option {i} ---")
        target = opt
        if not target.get('data-post'):
             target = opt.find('a', attrs={'data-post': True}) or opt
             
        post_id = target.get('data-post')
        nume = target.get('data-nume')
        data_nonce = target.get('data-nonce')
        type_val = target.get('data-type') or "tv"
        
        print(f"Post: {post_id}, Nume: {nume}, Nonce: {data_nonce}, Type: {type_val}")
        
        if post_id and nume:
            actions = ["player_ajax"] # Identified from JS
            
            # Gather potential nonce values
            potential_nonces = []
            if data_nonce: potential_nonces.append(data_nonce)
            if dt_ajax.get('nonce'): potential_nonces.append(dt_ajax['nonce'])
            if dt_ajax.get('security'): potential_nonces.append(dt_ajax['security'])
            
            potential_nonces = list(dict.fromkeys(potential_nonces))
            potential_nonce_keys = ["nonce", "security"]

            for action in actions:
                for nonce_val in potential_nonces:
                    for nonce_key in potential_nonce_keys:
                        payload = {
                            "action": action,
                            "post": post_id,
                            "nume": nume,
                            "type": type_val
                        }
                        payload[nonce_key] = nonce_val
                        
                        print(f"Testing: action={action}, {nonce_key}={nonce_val}")
                        try:
                            await asyncio.sleep(0.5)
                            r = await client.post(ajax_url, data=payload)
                            
                            if r.status_code == 200:
                                if 'src=' in r.text or 'iframe' in r.text:
                                    print(f"SUCCESS!!! Payload: {payload}\nResponse: {r.text[:200]}")
                                    return
                                elif r.text.strip() == '0':
                                    pass
                            else:
                                print(f"Response code: {r.status_code}")
                        except Exception as e:
                            print(f"Error: {e}")

    await client.aclose()

if __name__ == "__main__":
    asyncio.run(test())
