"""
API v1 路由汇总
"""
from fastapi import APIRouter
from app.api.v1 import hello, openai, video, subtitle, courses, lessons, tasks

# 创建v1版本的主路由
api_router = APIRouter()

# 注册各个子路由
api_router.include_router(hello.router, tags=["测试"])
api_router.include_router(openai.router, prefix="/openai", tags=["OpenAI"])
api_router.include_router(video.router, prefix="/videos", tags=["Videos"])
api_router.include_router(subtitle.router, prefix="/subtitles", tags=["Subtitles"])
api_router.include_router(courses.router, prefix="/courses", tags=["Courses"])
api_router.include_router(lessons.router, prefix="/lessons", tags=["Lessons"])
api_router.include_router(tasks.router, prefix="/tasks", tags=["Tasks"])

# 未来可以添加更多路由
# api_router.include_router(vocabulary.router, prefix="/vocabulary", tags=["单词本"])
# api_router.include_router(article.router, prefix="/articles", tags=["文章"])
