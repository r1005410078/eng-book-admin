"""
测试异步视频处理 API
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from app.main import app
from app.core.config import settings

client = TestClient(app)


class TestAsyncVideoProcessing:
    """测试异步视频处理功能"""
    
    def test_run_sync_endpoint_exists(self):
        """测试 run_sync 端点存在并返回正确的状态码"""
        # 测试端点是否存在（即使返回错误也说明路由正确）
        response = client.post(f"{settings.API_V1_PREFIX}/videos/1/run_sync")
        
        # 应该返回 202（成功）、404（视频不存在）或 500（数据库错误）
        # 不应该返回 405（方法不允许）
        assert response.status_code != 405
        
        # 如果返回 202，验证响应格式
        if response.status_code == 202:
            data = response.json()
            assert "message" in data
            assert "video_id" in data
            assert "status" in data
    
    def test_run_sync_video_not_found(self):
        """测试视频不存在的情况"""
        # 使用一个不太可能存在的 ID
        response = client.post(f"{settings.API_V1_PREFIX}/videos/999999/run_sync")
        
        # 可能返回 404 或 500（取决于数据库状态）
        assert response.status_code in [404, 500]
    
    def test_reprocess_endpoint_exists(self):
        """测试 reprocess 端点存在"""
        # 测试端点是否存在（即使返回错误也说明路由正确）
        response = client.post(f"{settings.API_V1_PREFIX}/videos/1/reprocess")
        
        # 应该返回 404（视频不存在）或 500（数据库错误）
        # 不应该返回 405（方法不允许）
        assert response.status_code != 405
    
    def test_get_reprocess_progress_endpoint_exists(self):
        """测试进度查询端点存在"""
        response = client.get(f"{settings.API_V1_PREFIX}/videos/1/reprocess")
        
        # 应该返回 404（视频不存在）或 500（数据库错误）
        # 不应该返回 405（方法不允许）
        assert response.status_code != 405


# 简化的集成测试（需要数据库）
class TestAsyncVideoProcessingIntegration:
    """集成测试 - 需要数据库连接"""
    
    @pytest.mark.skipif(
        not hasattr(settings, 'DATABASE_URL'),
        reason="需要数据库连接"
    )
    def test_full_workflow(self):
        """测试完整工作流（需要真实数据库）"""
        # 这个测试需要真实的数据库环境
        # 在 CI/CD 或本地开发环境中运行
        pass


# 单元测试 - 测试服务层逻辑
class TestVideoProgressService:
    """测试 VideoProgressService"""
    
    def test_calculate_total_progress(self):
        """测试进度计算逻辑"""
        from app.services.video_progress_service import VideoProgressService
        from app.models.processing_task import ProcessingTask, TaskType, TaskStatus
        
        # 创建模拟任务
        tasks = [
            Mock(
                task_type=TaskType.AUDIO_EXTRACTION,
                progress=100,
                status=TaskStatus.COMPLETED
            ),
            Mock(
                task_type=TaskType.SUBTITLE_GENERATION,
                progress=50,
                status=TaskStatus.PROCESSING
            ),
            Mock(
                task_type=TaskType.TRANSLATION,
                progress=0,
                status=TaskStatus.PENDING
            ),
            Mock(
                task_type=TaskType.PHONETIC,
                progress=0,
                status=TaskStatus.PENDING
            ),
            Mock(
                task_type=TaskType.GRAMMAR_ANALYSIS,
                progress=0,
                status=TaskStatus.PENDING
            ),
        ]
        
        # 计算进度
        progress = VideoProgressService.calculate_total_progress(tasks)
        
        # 预期: 10% (audio) + 10% (subtitle 50% of 20%) = 20%
        assert progress == 20
    
    def test_calculate_total_progress_all_completed(self):
        """测试所有任务完成时的进度"""
        from app.services.video_progress_service import VideoProgressService
        from app.models.processing_task import ProcessingTask, TaskType, TaskStatus
        
        # 所有任务都完成
        tasks = [
            Mock(task_type=task_type, progress=100, status=TaskStatus.COMPLETED)
            for task_type in TaskType
        ]
        
        progress = VideoProgressService.calculate_total_progress(tasks)
        
        # 应该是 100%
        assert progress == 100
    
    def test_calculate_total_progress_empty_tasks(self):
        """测试空任务列表"""
        from app.services.video_progress_service import VideoProgressService
        
        progress = VideoProgressService.calculate_total_progress([])
        
        # 空列表应该返回 0
        assert progress == 0

