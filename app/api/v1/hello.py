"""
Hello World API 路由
"""
from fastapi import APIRouter
from datetime import datetime
from typing import Dict, Any

router = APIRouter()

@router.get("/hello", summary="Hello World接口", tags=["测试"])
async def hello_world() -> Dict[str, Any]:
    """
    Hello World 测试接口
    
    返回:
        包含欢迎消息和当前时间的响应
    """
    return {
        "code": 200,
        "message": "成功",
        "data": {
            "greeting": "你好，欢迎使用英语学习管理后台！",
            "english": "Hello, Welcome to English Learning Admin System!",
            "timestamp": datetime.now().isoformat(),
            "version": "0.1.0"
        }
    }


@router.get("/health", summary="健康检查", tags=["系统"])
async def health_check() -> Dict[str, Any]:
    """
    系统健康检查接口
    
    返回:
        系统状态信息
    """
    return {
        "code": 200,
        "message": "成功",
        "data": {
            "status": "healthy",
            "service": "英语学习管理后台",
            "timestamp": datetime.now().isoformat()
        }
    }
