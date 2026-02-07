import undetected_chromedriver as uc
import time
import os

def fetch_hamot_api():
    print("Launching Local Browser to fetch API...")
    options = uc.ChromeOptions()
    
    driver = None
    try:
        driver = uc.Chrome(options=options)
        # Fetch the API endpoint directly
        driver.get("https://hamottv.rf.gd/?sys_load_api=1")
        
        print("Waiting for protection (20s)...")
        time.sleep(20)
        
        # Get the page text (which should be JSON)
        content = driver.find_element(by='tag name', value='body').text
        
        print("Saving Content...")
        output_path = os.path.join(os.path.dirname(__file__), "..", "hamot_api_dump.json")
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
    fetch_hamot_api()
