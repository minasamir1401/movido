
import requests

try:
    resp = requests.get("http://127.0.0.1:8000/anime/home")
    print(f"Status: {resp.status_code}")
    print(f"Data: {resp.json()}")
except Exception as e:
    print(f"Error: {e}")
