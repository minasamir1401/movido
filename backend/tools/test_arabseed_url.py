
import asyncio
import base64

# Test decoding an ArabSeed URL
safe_id = "aHR0cHM6Ly9hLmFzZC5ob21lcy8lZDklODElZDklOGElZDklODQlZDklODUtc2VsZi1oZWxwLTIwMjUtJWQ5JTg1JWQ4JWFhJWQ4JWIxJWQ4JWFjJWQ5JTg1Lw"

# Add padding if needed
temp_id = safe_id
padding = len(temp_id) % 4
if padding: 
    temp_id += "=" * (4 - padding)

try:
    decoded_url = base64.urlsafe_b64decode(temp_id).decode()
    print(f"Decoded URL: {decoded_url}")
    
    # Check routing
    if "larozavideo" in decoded_url or "laroza" in decoded_url:
        print("Will route to: Larooza")
    elif "asd.homes" in decoded_url or "arabseed" in decoded_url:
        print("Will route to: ArabSeed")
    else:
        print("Will route to: Fallback (Larooza first)")
        
except Exception as e:
    print(f"Error: {e}")
