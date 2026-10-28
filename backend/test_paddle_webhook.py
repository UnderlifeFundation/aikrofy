import json
import requests

def test_paddle_webhook():
    webhook_url = "http://localhost:5010/webhooks/paddle"
    
    # Mock payload for a subscription.created event
    # passthrough="1" maps to Company ID 1
    # price ID matches Sandbox Jab plan
    payload = {
        "event_type": "subscription.created",
        "data": {
            "id": "sub_test_12345",
            "status": "active",
            "passthrough": "1",
            "items": [
                {
                    "price": {
                        "id": "pri_01j00000000000000000000001"
                    }
                }
            ],
            "custom_data": {
                "company_id": 1
            }
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "Paddle-Signature": "ts=1692609120;h1=mocked_signature_hash" # Dummy signature, bypassed by our sandbox helper
    }
    
    print(f"Sending mock webhook request to {webhook_url}...")
    try:
        response = requests.post(webhook_url, json=payload, headers=headers)
        print(f"Response status code: {response.status_code}")
        print(f"Response payload: {response.json()}")
    except Exception as e:
        print(f"Failed to post to webhook: {e}")

if __name__ == '__main__':
    test_paddle_webhook()
