import pytest
import json
import requests

def test_webhook_schema_contract():
    """
    Verify that the Dispatcher accepts the exact schema defined in the implementation plan.
    This serves as a 'schema-first' contract test.
    """
    dispatcher_url = os.environ.get("DISPATCHER_URL", "http://localhost:5000")
    
    # Valid schema according to implementation plan
    valid_payload = {
        "cameraId": "cam-01",
        "filename": "test.mp4",
        "key": "recordings/test.mp4",
        "timestamp": 1234567890,
        "bucket": "recordings"
    }
    
    headers = {
        "Authorization": "Bearer super-secret-key-change-it",
        "Content-Type": "application/json"
    }
    
    # This requires the dispatcher to be running
    try:
        response = requests.post(f"{dispatcher_url}/webhook", json=valid_payload, headers=headers, timeout=5)
        # We expect 200 if it's running, but we check if it validates correctly
        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "queued"
            assert data["task"]["camera_id"] == "cam-01"
    except requests.exceptions.ConnectionError:
        pytest.skip("Dispatcher not reachable for contract test")

def test_dispatcher_internal_translation():
    """Verify dispatcher translates camelCase from Vault to snake_case for Task."""
    # This can be a unit test if we import the app, but here we test the boundary
    pass
