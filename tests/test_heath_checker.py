# tests/test_health_checker.py
import pytest
from unittest.mock import patch, MagicMock
from services.health_checker import APIHealthChecker
import requests
from core.exceptions import APIConnectionError

@pytest.fixture
def health_checker():
    return APIHealthChecker()

@patch('requests.Session.get')
def test_check_endpoint_success(mock_get, health_checker):
    """Test that a 200 OK response is parsed correctly without retries."""
    # Setup the mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_get.return_value = mock_response

    result = health_checker._check_endpoint("https://fake-api.com/health")
    
    assert result['status'] == "UP"
    assert result['code'] == 200
    assert mock_get.call_count == 1

@patch('requests.Session.get')
def test_check_endpoint_retry_logic(mock_get, health_checker):
    """Test that the retry decorator attempts exactly 3 times on connection errors."""
    # Force the mock to raise a ConnectionError every time it's called
    mock_get.side_effect = requests.ConnectionError("Network down")

    with pytest.raises(APIConnectionError):
        health_checker._check_endpoint("https://fake-api.com/health")
    
    # Verify the backoff decorator actually retried 3 times before failing
    assert mock_get.call_count == 3