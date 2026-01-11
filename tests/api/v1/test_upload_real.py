"""
真实文件上传测试
使用 assets/test.mp4 进行测试
"""
import os
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)

# 资源文件路径
TEST_VIDEO_PATH = "assets/test.mp4"

@pytest.fixture
def check_test_file():
    """确保测试文件存在"""
    if not os.path.exists(TEST_VIDEO_PATH):
        pytest.skip(f"Test file not found: {TEST_VIDEO_PATH}")

@patch("app.api.v1.video.process_uploaded_video.delay")
def test_upload_real_video(mock_process_task, check_test_file):
    """测试上传真实的 MP4 文件"""
    
    # 模拟 Celery 任务 ID 返回
    mock_process_task.return_value = MagicMock(id="fake-task-id")
    
    file_stats = os.stat(TEST_VIDEO_PATH)
    file_size = file_stats.st_size
    
    # 打开真实文件进行上传
    with open(TEST_VIDEO_PATH, "rb") as f:
        response = client.post(
            f"{settings.API_V1_PREFIX}/videos/upload",
            files={"file": ("test_upload.mp4", f, "video/mp4")},
            data={
                "title": "Real Upload Test Video",
                "description": "Integration test with real file",
                "category": "Testing",
                "difficulty_level": "intermediate"
            }
        )
    
    # 验证响应
    assert response.status_code == 200, f"Upload failed: {response.text}"
    data = response.json()
    
    # 验证返回数据
    assert data["title"] == "Real Upload Test Video"
    assert data["status"] == "uploading"
    assert "id" in data
    assert "created_at" in data
    
    # 验证后台任务是否被触发
    mock_process_task.assert_called_once()
    
    # 获取任务调用的参数 (video_id)
    args, _ = mock_process_task.call_args
    uploaded_video_id = args[0]
    assert uploaded_video_id == data["id"]
    
    print(f"\n✅ Video uploaded successfully! ID: {data['id']}")
