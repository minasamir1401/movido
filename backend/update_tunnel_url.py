import os
import re
import time
import sys

def update_env(url):
    """Update .env file with cloudflared tunnel URL"""
    env_path = os.path.join(os.path.dirname(__file__), "..", "meih-netflix-clone", ".env")
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(env_path), exist_ok=True)
    
    # Create or update .env
    if not os.path.exists(env_path):
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(f"VITE_API_URL={url}\n")
            f.write(f"VITE_API_BASE_URL={url}\n")
        print(f"[SUCCESS] Created .env with tunnel URL: {url}")
        return True

    # Read existing content
    with open(env_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Update or add URLs
    new_lines = []
    found_url = False
    found_base = False
    
    for line in lines:
        if line.strip().startswith("VITE_API_URL="):
            new_lines.append(f"VITE_API_URL={url}\n")
            found_url = True
        elif line.strip().startswith("VITE_API_BASE_URL="):
            new_lines.append(f"VITE_API_BASE_URL={url}\n")
            found_base = True
        else:
            new_lines.append(line)

    if not found_url:
        new_lines.append(f"VITE_API_URL={url}\n")
    if not found_base:
        new_lines.append(f"VITE_API_BASE_URL={url}\n")

    # Write back
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    
    print(f"[SUCCESS] Updated .env with tunnel URL: {url}")
    return True

def get_tunnel_url_from_log():
    """Extract cloudflared tunnel URL from log file"""
    log_path = os.path.join(os.path.dirname(__file__), "logs", "tunnel.log")
    
    if not os.path.exists(log_path):
        return None
    
    try:
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
            
            # Pattern for cloudflare tunnel URL
            patterns = [
                r"https://[a-z0-9-]+\.trycloudflare\.com",
                r"https://[a-zA-Z0-9-]+\.trycloudflare\.com",
                r"INF \|\s+(https://[^\s]+\.trycloudflare\.com)",
            ]
            
            for pattern in patterns:
                match = re.search(pattern, content)
                if match:
                    url = match.group(1) if len(match.groups()) > 0 else match.group(0)
                    # Validate URL
                    if "trycloudflare.com" in url:
                        return url.strip()
    except Exception as e:
        print(f"[ERROR] Failed to read log: {e}")
    
    return None

def wait_for_tunnel(max_attempts=60, interval=2):
    """Wait for cloudflared tunnel to establish and extract URL"""
    print("[SYSTEM] ⏳ Waiting for Cloudflare Tunnel to establish...")
    print(f"[SYSTEM] Will check every {interval}s for up to {max_attempts * interval}s")
    
    for attempt in range(1, max_attempts + 1):
        url = get_tunnel_url_from_log()
        
        if url:
            print(f"[SUCCESS] ✅ Found tunnel URL after {attempt * interval}s: {url}")
            return url
        
        # Progress indicator
        if attempt % 5 == 0:
            print(f"[SYSTEM] Still waiting... (attempt {attempt}/{max_attempts})")
        
        time.sleep(interval)
    
    print(f"[ERROR] ❌ Could not find tunnel URL after {max_attempts * interval}s")
    return None

if __name__ == "__main__":
    print("=" * 70)
    print("  CLOUDFLARE TUNNEL URL SYNCHRONIZER")
    print("=" * 70)
    
    # Wait for tunnel URL
    tunnel_url = wait_for_tunnel(max_attempts=60, interval=2)
    
    if tunnel_url:
        # Update .env file
        if update_env(tunnel_url):
            print("\n[SYSTEM] ✅ Configuration updated successfully!")
            print(f"[SYSTEM] 🌐 Tunnel URL: {tunnel_url}")
            print(f"[SYSTEM] 📝 Frontend .env has been updated")
            print("\n[NEXT STEP] Please restart the frontend (npm run dev) to apply changes")
            sys.exit(0)
        else:
            print("\n[ERROR] ❌ Failed to update .env file")
            sys.exit(1)
    else:
        print("\n[ERROR] ❌ Tunnel URL not found. Check if cloudflared is running.")
        print("[HINT] Check backend/logs/tunnel.log for more details")
        sys.exit(1)
