import time
from locust import HttpUser, task, between

class VideoUploadUser(HttpUser):
    """
    Simulates a Kerberos Vault instance sending webhooks to the Dispatcher.
    """
    wait_time = between(1, 5)  # Simulate 12-60 webhooks per minute per 'agent'
    
    @task
    def upload_video(self):
        # Simulate Kerberos Vault webhook format
        self.client.post("/webhook", json={
            "cameraId": "load-test-cam-01",
            "filename": f"load_test_{int(time.time())}.mp4",
            "key": f"recordings/load_test_{int(time.time())}.mp4",
            "timestamp": int(time.time()),
            "bucket": "recordings"
        }, headers={"Authorization": "Bearer super-secret-key-change-it"})

# Run with:
# locust -f tests/load/locustfile.py --host=http://localhost:5000
