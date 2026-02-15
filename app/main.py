"""
FastAPI 应用主入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.router import api_router

# 创建FastAPI应用实例
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="英语学习应用管理后台API",
    docs_url="/docs",
    redoc_url="/redoc",
)

# 配置CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该配置具体的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 注册API路由
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

from fastapi.staticfiles import StaticFiles
import os

# 确保上传目录存在
if not os.path.exists(settings.UPLOAD_DIR):
    os.makedirs(settings.UPLOAD_DIR)

# 挂载静态文件目录 (用于访问上传的视频/图片)
# 注意: 生产环境建议使用 Nginx
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


@app.get("/", tags=["根路径"])
async def root():
    """
    根路径接口
    
    返回:
        欢迎信息和API文档链接
    """
    return {
        "code": 200,
        "message": "成功",
        "data": {
            "service": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "docs": "/docs",
            "redoc": "/redoc",
            "api_v1": settings.API_V1_PREFIX
        }
    }


@app.on_event("startup")
async def startup_event():
    """应用启动时执行"""
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} 启动成功！")
    print(f"📚 API文档: http://localhost:8000/docs")
    print(f"📖 ReDoc文档: http://localhost:8000/redoc")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时执行"""
    print(f"👋 {settings.APP_NAME} 已关闭")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # 开发模式下启用热重载
    )

