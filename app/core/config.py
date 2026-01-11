"""
应用配置模块
"""
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置类"""
    
    # 基本配置
    APP_NAME: str = "英语学习管理后台"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    
    # API配置
    API_V1_PREFIX: str = "/api/v1"
    
    # 数据库配置
    DATABASE_URL: Optional[str] = None
    
    # Redis配置
    REDIS_URL: Optional[str] = None
    
    # OpenAI配置
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_API_KEY: Optional[str] = None
    
    # 文件上传配置
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 2147483648  # 2GB
    
    # JWT配置
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 创建全局配置实例
settings = Settings()
