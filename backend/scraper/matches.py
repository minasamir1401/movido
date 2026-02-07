import undetected_chromedriver as uc
import logging
import json
import time
import asyncio
import httpx
from typing import List, Dict, Any
from urllib.parse import quote

logger = logging.getLogger("matches_scraper")

class MatchesScraper:
    BASE_URL = "https://hamottv.rf.gd/?sys_load_api=1"
    COOKIE_URL = "https://hamottv.rf.gd/"
    
    def __init__(self):
        self._cache = []
        self._last_update = 0
        self._cache_duration = 3600 # 1 hour cache (speed optimization)
        self._cookies = {}
        self._user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        
        # Start pre-fetch in background if loop is running
        try:
            asyncio.create_task(self._prefetch_data())
        except RuntimeError:
            pass # No loop running, that's fine (e.g. script import)

    async def _prefetch_data(self):
        """Fetches data in background on startup"""
        logger.info("🚀 Starting fast pre-fetch for Matches...")
        await self.fetch_matches()

    async def fetch_matches(self) -> List[Dict[str, Any]]:
        # 1. Return Cache if valid (INSTANT)
        if self._cache and (time.time() - self._last_update < self._cache_duration):
            return self._cache

        # 2. Try Local File (Reliable)
        try:
            import os
            if os.path.exists("backend/hamot_servers.json"):
                with open("backend/hamot_servers.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._cache = self._parse_hamot_json(data)
                    self._last_update = time.time()
                    return self._cache
        except Exception as e:
            logger.warning(f"Failed to load local file: {e}")

        # 3. Try HTTPX with existing cookies (FAST)
        if self._cookies:
            try:
                logger.info("⚡ Fetching matches via fast HTTP...")
                async with httpx.AsyncClient(
                    headers={"User-Agent": self._user_agent}, 
                    cookies=self._cookies,
                    verify=False,
                    timeout=10.0,
                    follow_redirects=True
                ) as client:
                    resp = await client.get(self.BASE_URL)
                    if resp.status_code == 200 and "{" in resp.text:
                        # Validate it's likely JSON
                        try:
                            # Extract JSON part just in case
                            text = resp.text
                            if text.strip().startswith("<html>"): # Protection page
                                raise Exception("Protection detected")
                            
                            json_start = text.find("{")
                            json_end = text.rfind("}") + 1
                            if json_start != -1:
                                data = json.loads(text[json_start:json_end])
                                self._cache = self._parse_hamot_json(data)
                                self._last_update = time.time()
                                return self._cache
                        except Exception:
                            pass # Fallback to browser
            except Exception as e:
                logger.warning(f"Fast fetch failed: {e}")

        # 3. Fallback to Browser (SLOW but needed once)
        logger.info("🛡️ Fast fetch failed. Launching browser to bypass protection...")
        channels = await asyncio.to_thread(self._run_browser_extraction)
        
        if channels:
            self._cache = channels
            self._last_update = time.time()
            return channels
        
        return self._cache if self._cache else [] # Return stale cache if fails

    async def get_cookies(self, force_refresh: bool = False) -> Dict[str, str]:
        """Ensures valid cookies are available for proxying"""
        if self._cookies and not force_refresh:
            return self._cookies
            
        logger.info("🍪 Refreshing HamotTV cookies...")
        await asyncio.to_thread(self._run_browser_extraction, only_cookies=True)
        return self._cookies

    def _run_browser_extraction(self, only_cookies: bool = False):
        driver = None
        try:
            # Cleanup UC leftovers to prevent [WinError 183]
            try:
                import shutil
                import os
                uc_path = os.path.join(os.environ.get('APPDATA', ''), 'undetected_chromedriver')
                if os.path.exists(uc_path):
                    # Only remove the exe if it's causing issues, or the whole dir
                    # Removing the whole dir ensures a fresh start
                    for f in os.listdir(uc_path):
                        if f.endswith(".exe"):
                            try: os.remove(os.path.join(uc_path, f))
                            except: pass
            except:
                pass

            options = uc.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            
            # Try to detect Chrome version to prevent mismatch
            version_main = None
            try:
                import winreg
                keys = [
                    (winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon"),
                    (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe")
                ]
                for root, path in keys:
                    try:
                        with winreg.OpenKey(root, path) as key:
                            v, _ = winreg.QueryValueEx(key, "version" if "BLBeacon" in path else "DisplayVersion")
                            if v:
                                version_main = int(v.split('.')[0])
                                break
                    except: continue
                
                # Fallback to file path inspection if registry fails
                if not version_main:
                    chrome_path = r"C:\Program Files\Google\Chrome\Application"
                    if os.path.exists(chrome_path):
                        for item in os.listdir(chrome_path):
                            if item[0].isdigit() and '.' in item:
                                version_main = int(item.split('.')[0])
                                break
            except: pass

            # Hard fallback to a safe version if still None
            if not version_main: version_main = 130 

            driver = uc.Chrome(options=options, version_main=version_main)
            driver.set_page_load_timeout(60)
            
            # 1. Go to main page to get cookies
            driver.get(self.COOKIE_URL)
            time.sleep(10) # Wait for challenge
            
            # Save cookies for next time (The Secret Sauce for Speed)
            self._cookies = {c['name']: c['value'] for c in driver.get_cookies()}
            self._user_agent = driver.execute_script("return navigator.userAgent;")
            
            # 2. Go to API (if we need data)
            if only_cookies:
                return []
                
            driver.get(self.BASE_URL)
            body_text = driver.find_element("tag name", "body").text
            
            if "{" in body_text:
                json_str = body_text[body_text.find("{"):body_text.rfind("}")+1]
                data = json.loads(json_str)
                return self._parse_hamot_json(data)
            
            return []
            
        except Exception as e:
            # Silence common shutdown errors to keep logs clean
            if "CancelledError" in str(e) or "shutdown" in str(e).lower():
                pass
            else:
                logger.error(f"Browser extraction failed: {e}")
            return []
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass

    def _parse_hamot_json(self, data: Dict) -> List[Dict[str, Any]]:
        results = []
        for category, channels in data.items():
            for ch_key, ch_data in channels.items():
                raw_url = ch_data.get("source", "")
                proxied_url = f"http://localhost:8000/proxy/stream?url={quote(raw_url)}" if raw_url else ""
                
                results.append({
                    "team_home": ch_data.get("name", "Unknown Channel"),
                    "team_away": "", 
                    "time": "LIVE",
                    "status": "Online",
                    "url": proxied_url,
                    "logo_home": ch_data.get("image", ""),
                    "logo_away": "",
                    "score": "TV"
                })
        return results

matches_scraper = MatchesScraper()
