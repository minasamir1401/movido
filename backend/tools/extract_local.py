import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import time
import json
import os

def fetch_hamot_local():
    print("Launching Local Browser (Undetected)...")
    options = uc.ChromeOptions()
    # options.add_argument('--headless') # Headless might trigger detection
    
    driver = None
    try:
        driver = uc.Chrome(options=options)
        driver.get("https://hamottv.rf.gd/")
        
        print("Waiting for protection (20s)...")
        time.sleep(20)
        
        content = driver.page_source
        
        print("Saving Content...")
        # Save to backend folder so I can read it
        output_path = os.path.join(os.path.dirname(__file__), "..", "hamot_local_dump.html")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        print(f"Done. Saved to {output_path}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

if __name__ == "__main__":
    fetch_hamot_local()
