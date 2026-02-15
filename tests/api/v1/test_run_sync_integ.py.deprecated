"""
同步处理接口的真实集成测试
"""
import os
import pytest
import time
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.models.video import VideoStatus

client = TestClient(app)

# 资源文件路径
TEST_VIDEO_PATH = "assets/test.mp4"

@pytest.fixture
def check_test_file():
    """确保测试文件存在"""
    if not os.path.exists(TEST_VIDEO_PATH):
        pytest.skip(f"Test file not found: {TEST_VIDEO_PATH}")

@patch("app.tasks.subtitle_tasks.openai_service") # 仍然 mock OpenAI 以避免费用和网络依赖
def test_sync_processing_integration(mock_openai, check_test_file):
    """
    真实集成测试：上传视频 -> 同步执行处理
    验证：FFmpeg 提取, Whisper 转录, 数据库更新
    """
    # -------------------------------------------------------------------------
    # 1. 上传视频
    # -------------------------------------------------------------------------
    print("\n[1] Uploading video...")
    
    # 模拟 Celery 任务，防止上传时自动触发异步处理干扰已有的逻辑
    # 我们希望上传后处于 uploading 状态，然后手动调 sync 接口
    # 在真实环境中，上传接口会触发 process_uploaded_video.delay
    # 如果 worker 没开，任务会积压。如果 worker 开了，它会抢在我们的 sync 调用之前执行。
    # 为了测试 sync 接口，我们需要确保上传后，我们可以控制何时处理。
    # 现在的实现是：上传接口 -> process_uploaded_video.delay()
    # 我们可以 patch process_uploaded_video.delay 让它失效。
    
    with patch("app.api.v1.video.process_uploaded_video.delay") as mock_delay:
        with open(TEST_VIDEO_PATH, "rb") as f:
            response = client.post(
                f"{settings.API_V1_PREFIX}/videos/upload",
                files={"file": ("sync_test.mp4", f, "video/mp4")},
                data={
                    "title": "Sync Processing Test",
                    "description": "Integration test for sync processing endpoint",
                    "difficulty_level": "intermediate"
                }
            )
        assert response.status_code == 200, f"Upload failed: {response.text}"
        video_data = response.json()
        video_id = video_data["id"]
        print(f"Video uploaded. ID: {video_id}")
        
    # -------------------------------------------------------------------------
    # 2. 设置 OpenAI Mock 返回 (针对 Async 方法)
    # -------------------------------------------------------------------------
    async def mock_translate(*args, **kwargs):
        return ["Mock Translation"] * 50
        
    async def mock_phonetic(*args, **kwargs):
        return ["Mock Phonetic"] * 50
        
    async def mock_grammar(texts, batch_size=5):
        # 根据输入文本数量返回对应数量的语法分析结果
        results = []
        for _ in texts:
            results.append({
                "sentence_structure": "Subject + Verb",
                "explanation": "Mock Grammar Explanation",
                "keywords": ["mock", "test"]
            })
        return results

    mock_openai.batch_translate_text.side_effect = mock_translate
    mock_openai.batch_generate_phonetic.side_effect = mock_phonetic
    mock_openai.batch_analyze_grammar.side_effect = mock_grammar

    # -------------------------------------------------------------------------
    # 3. 调用同步处理接口
    # -------------------------------------------------------------------------
    print(f"[2] Calling sync processing endpoints for video {video_id}...")
    print("This might take a while depending on video length and Whisper model...")
    
    start_time = time.time()
    response = client.post(f"{settings.API_V1_PREFIX}/videos/{video_id}/run_sync")
    duration = time.time() - start_time
    
    if response.status_code != 200:
        print(f"Failed response: {response.text}")
        
    assert response.status_code == 200
    result = response.json()
    
    if result["status"] != "completed":
        print(f"\n[ERROR] Video processing failed with status: {result['status']}")
        
        # 获取任务详情以查看具体错误
        resp_status = client.get(f"{settings.API_V1_PREFIX}/videos/{video_id}/status")
        tasks = resp_status.json()
        print("\n[Task Details]:")
        for t in tasks:
            print(f"- Task: {t['task_type']}, Status: {t['status']}, Error: {t.get('error_message')}")
    
    assert result["status"] == "completed"
    
    # -------------------------------------------------------------------------
    # 4. 验证结果
    # -------------------------------------------------------------------------
    print("[3] Verifying results...")
    
    # 4.1 检查视频详情
    resp_video = client.get(f"{settings.API_V1_PREFIX}/videos/{video_id}")
    video_info = resp_video.json()
    assert video_info["status"] == "completed"
    assert video_info["duration"] is not None
    assert video_info["thumbnail_path"] is not None
    
    # 4.2 检查字幕
    resp_subs = client.get(f"{settings.API_V1_PREFIX}/videos/{video_id}/subtitles")
    subtitles = resp_subs.json()
    assert len(subtitles) > 0, "No subtitles generated"
    print(f"Generated {len(subtitles)} subtitles.")
    
    # 检查第一条字幕是否包含 mock 的翻译
    first_sub = subtitles[0]
    assert first_sub["translation"] == "Mock Translation"
    assert first_sub["phonetic"] == "Mock Phonetic"
    
    # 4.3 检查物理文件是否存在 (需要知道 ID 生成的具体路径)
    # 我们知道 ID 是 video_id
    import os
    # 假设默认上传目录结构: uploads/videos/{id}/subtitles.srt
    srt_path = f"uploads/videos/{video_id}/subtitles.srt"
    
    assert os.path.exists(srt_path), f"SRT file not found at {srt_path}"
    
    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read()
        print(f"\n[SRT Content Preview]:\n{content[:200]}")
        # 验证是否包含双语 (mock 的翻译)
        assert "Mock Translation" in content, "SRT file does not contain translation"
    
    print("✅ Integration test passed!")
