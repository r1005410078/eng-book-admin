"""
API v1 路由汇总
"""
from fastapi import APIRouter
from app.api.v1 import hello, openai

# 创建v1版本的主路由
api_router = APIRouter()

# 注册各个子路由
api_router.include_router(hello.router, tags=["测试"])
api_router.include_router(openai.router, prefix="/openai", tags=["OpenAI"])

# 未来可以添加更多路由
# api_router.include_router(vocabulary.router, prefix="/vocabulary", tags=["单词本"])
# api_router.include_router(article.router, prefix="/articles", tags=["文章"])
# api_router.include_router(video.router, prefix="/videos", tags=["视频"])

