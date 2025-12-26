"""
E2E Health Check
================
Verifies the full system stack is up and running.
"""

import pytest
import requests
import time
import os

APP_URL = os.getenv("APP_URL", "http://app:8501")

def test_dashboard_is_accessible():
    """Verify Streamlit dashboard returns 200 OK."""
    # Retry loop because app might take seconds to bind port
    max_retries = 30
    for i in range(max_retries):
        try:
            response = requests.get(f"{APP_URL}/_stcore/health", timeout=2)
            if response.status_code == 200:
                assert response.text == "ok"
                return
        except requests.exceptions.ConnectionError:
            time.sleep(2)
            
    pytest.fail(f"Could not connect to {APP_URL} after {max_retries} attempts")
