"""
FFmpeg 服务测试
"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.services.ffmpeg_service import FFmpegService

@pytest.fixture
def ffmpeg_service():
    return FFmpegService()

@patch("ffmpeg.probe")
def test_get_video_metadata(mock_probe, ffmpeg_service):
    """测试获取视频元数据"""
    # 模拟 ffmpeg.probe 返回
    mock_probe.return_value = {
        'streams': [
            {
                'codec_type': 'video',
                'width': 1920,
                'height': 1080,
                'codec_name': 'h264'
            }
        ],
        'format': {
            'duration': '60.5',
            'bit_rate': '1000000',
            'size': '1024000'
        }
    }
    
    metadata = ffmpeg_service.get_video_metadata(Path("dummy.mp4"))
    
    assert metadata["duration"] == 60.5
    assert metadata["resolution"] == "1920x1080"
    assert metadata["format"] == "h264"
    assert metadata["size"] == 1024000
