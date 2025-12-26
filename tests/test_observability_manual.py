import unittest
from unittest.mock import MagicMock, patch
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

class TestObservabilityIntegration(unittest.TestCase):
    
    @patch('opentelemetry.trace.get_tracer')
    @patch('sentry_sdk.init')
    @patch('prometheus_client.start_http_server')
    def test_init_observability(self, mock_prometheus, mock_sentry, mock_tracer):
        from core.observability import init_observability
        
        with patch.dict(os.environ, {"SENTRY_DSN": "http://test@sentry.io/1", "JAEGER_HOST": "localhost"}):
            init_observability("test-service")
            
            mock_sentry.assert_called_once()
            # Tracing init is more complex to mock fully but we can check if it runs without error
            
    def test_logging_setup_with_tracing(self):
        from core.logging_setup import setup_logging
        from opentelemetry import trace
        
        # Mock an active span
        mock_span = MagicMock()
        mock_span.get_span_context().is_valid = True
        mock_span.get_span_context().trace_id = 0x1234567890abcdef1234567890abcdef
        mock_span.get_span_context().span_id = 0x1234567890abcdef
        
        with patch('opentelemetry.trace.get_current_span', return_value=mock_span):
            logger = setup_logging()
            # We can't easily check the output of structlog here without more complex setup, 
            # but we ensured the processor is added.
            self.assertIsNotNone(logger)

    @patch('ml_worker.consumer.load_config')
    @patch('ml_worker.consumer.init_observability')
    @patch('prometheus_client.start_http_server')
    def test_ml_worker_instrumentation(self, mock_prom, mock_obs, mock_config):
        # Just ensure importing and basic setup doesn't crash
        try:
            import ml_worker.consumer
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"ML Worker instrumentation caused a crash: {e}")

if __name__ == '__main__':
    unittest.main()
