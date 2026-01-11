"""
Whisper 服务测试
"""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from app.services.whisper_service import WhisperService

@pytest.fixture
def whisper_service():
    return WhisperService()

@patch("whisper.load_model")
def test_transcribe(mock_load_model, whisper_service):
    """测试转录功能"""
    # 模拟模型和转录结果
    mock_model = MagicMock()
    mock_model.transcribe.return_value = {
        "segments": [
            {
                "start": 0.0,
                "end": 2.0,
                "text": " Hello world ",
                "avg_logprob": -0.5
            },
            {
                "start": 2.0,
                "end": 4.0,
                "text": " This is a test ",
                "avg_logprob": -0.4
            }
        ]
    }
    mock_load_model.return_value = mock_model
    
    # 创建一个 dummy 音频文件以通过 exists 检查
    with patch("pathlib.Path.exists", return_value=True):
        result = whisper_service.transcribe(Path("dummy.wav"))
        
    assert len(result) == 2
    assert result[0]["sequence_number"] == 1
    assert result[0]["original_text"] == "Hello world"
    assert result[1]["start_time"] == 2.0
