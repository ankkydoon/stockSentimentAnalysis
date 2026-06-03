import pytest
from unittest.mock import patch, MagicMock
from agents.hf_client import hf_post

def test_hf_post_retries_on_503():
    mock_fail = MagicMock(status_code=503)
    mock_ok = MagicMock(status_code=200)
    mock_ok.json.return_value = [{"label": "positive", "score": 0.9}]
    with patch("agents.hf_client.requests.post", side_effect=[mock_fail, mock_ok]):
        result = hf_post("https://api-inference.huggingface.co/models/test",
                         {"inputs": "hello"}, token="tok", retries=2, backoff_base=0.0)
    assert result == [{"label": "positive", "score": 0.9}]

def test_hf_post_raises_after_max_retries():
    mock_fail = MagicMock(status_code=503)
    mock_fail.text = "Service Unavailable"
    with patch("agents.hf_client.requests.post", return_value=mock_fail):
        with pytest.raises(RuntimeError, match="HF API failed"):
            hf_post("https://api-inference.huggingface.co/models/test",
                    {"inputs": "hello"}, token="tok", retries=2, backoff_base=0.0)
