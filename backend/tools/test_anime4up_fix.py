import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import json
from scraper.anime4up import anime4up_scraper

async def main():
    print("Fetching Home...")
    home = await anime4up_scraper.fetch_home()
    
    items_to_test = []
    for section, items in home.items():
        for item in items:
            items_to_test.append(item)
            if len(items_to_test) >= 5: break
        if len(items_to_test) >= 5: break
            
    print(f"Found {len(items_to_test)} items to test.")
    
    for i, item in enumerate(items_to_test):
        print(f"\nTEST {i+1}/{len(items_to_test)}: {item['title']} ({item['id']})")
        try:
            details = await anime4up_scraper.fetch_details(item['id'])
            print(f"  > Title: {details.get('title', '').encode('utf-8', 'replace').decode()}")
            
            ep_to_check = None
            if details.get('type') == 'series':
                if details.get('episodes'):
                    ep_to_check = details['episodes'][0]
                    print(f"  > Series with {len(details['episodes'])} episodes. Checking first episode...")
                else:
                    print("  > Series but NO episodes found!")
            else:
                ep_to_check = details # Single movie/episode
            
            if ep_to_check:
                if 'url' in ep_to_check: # It's an episode from the list
                    ep_id = ep_to_check['id']
                    ep_details = await anime4up_scraper.fetch_episode(ep_id)
                else:
                    ep_details = ep_to_check
                
                print(f"  > Servers: {len(ep_details.get('servers', []))}")
                if len(ep_details.get('servers', [])) > 0:
                    print(f"    - First Server: {ep_details['servers'][0]['name'].encode('utf-8', 'replace').decode()}")
                else:
                    print("    !! NO SERVERS FOUND !!")
                    
                print(f"  > Downloads: {len(ep_details.get('download_links', []))}")
            
        except Exception as e:
            print(f"  !! ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(main())
