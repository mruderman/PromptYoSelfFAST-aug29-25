import requests

url = "http://localhost:8000/mcp/sse"
headers = {"Accept": "text/event-stream"}

with requests.get(url, headers=headers, stream=True) as resp:
    print(f"Status: {resp.status_code}")
    count = 0
    for line in resp.iter_lines():
        if line:
            decoded = line.decode()
            if decoded.startswith("data: "):
                print(decoded[6:])
                count += 1
                if count >= 5:
                    break 