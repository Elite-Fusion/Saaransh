import requests

payload = {
    "request_id": "test-001",
    "question": "How many theft cases were reported in Mysuru?",
}

response = requests.post(
    "http://127.0.0.1:8000/api/v1/ai/investigate",
    json=payload,
    timeout=30,
)
print(response.status_code)
print(response.text)
