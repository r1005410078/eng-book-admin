"""
OpenAI 测试 API
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
from app.services.openai_service import openai_service
from app.core.config import settings

router = APIRouter()


class TranslateRequest(BaseModel):
    """翻译请求模型"""
    text: str
    target_language: str = "中文"


class GrammarAnalysisRequest(BaseModel):
    """语法分析请求模型"""
    sentence: str


class PhoneticRequest(BaseModel):
    """音标生成请求模型"""
    text: str
    accent: str = "美式"


@router.get("/test", summary="测试OpenAI连接", tags=["OpenAI"])
async def test_openai_connection() -> Dict[str, Any]:
    """
    测试 OpenAI API 连接
    
    返回:
        连接状态信息
    """
    try:
        is_connected = openai_service.test_connection()
        
        return {
            "code": 200,
            "message": "成功",
            "data": {
                "connected": is_connected,
                "base_url": settings.OPENAI_BASE_URL,
                "api_key_configured": settings.OPENAI_API_KEY is not None,
                "api_key_prefix": settings.OPENAI_API_KEY[:10] + "..." if settings.OPENAI_API_KEY else None
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"连接测试失败: {str(e)}")


@router.post("/translate", summary="翻译文本", tags=["OpenAI"])
async def translate_text(request: TranslateRequest) -> Dict[str, Any]:
    """
    翻译文本
    
    参数:
        request: 翻译请求，包含要翻译的文本和目标语言
        
    返回:
        翻译结果
    """
    try:
        translation = await openai_service.translate_text(
            text=request.text,
            target_language=request.target_language
        )
        
        return {
            "code": 200,
            "message": "成功",
            "data": {
                "original_text": request.text,
                "translated_text": translation,
                "target_language": request.target_language
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/grammar", summary="语法分析", tags=["OpenAI"])
async def analyze_grammar(request: GrammarAnalysisRequest) -> Dict[str, Any]:
    """
    分析句子语法
    
    参数:
        request: 语法分析请求，包含要分析的句子
        
    返回:
        语法分析结果
    """
    try:
        analysis = await openai_service.analyze_grammar(sentence=request.sentence)
        
        return {
            "code": 200,
            "message": "成功",
            "data": {
                "sentence": request.sentence,
                "analysis": analysis
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/phonetic", summary="生成音标", tags=["OpenAI"])
async def generate_phonetic(request: PhoneticRequest) -> Dict[str, Any]:
    """
    生成音标
    
    参数:
        request: 音标生成请求，包含文本和口音类型
        
    返回:
        音标结果
    """
    try:
        phonetic = await openai_service.generate_phonetic(
            text=request.text,
            accent=request.accent
        )
        
        return {
            "code": 200,
            "message": "成功",
            "data": {
                "text": request.text,
                "phonetic": phonetic,
                "accent": request.accent
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config", summary="查看OpenAI配置", tags=["OpenAI"])
async def get_openai_config() -> Dict[str, Any]:
    """
    查看当前 OpenAI 配置（不显示完整 API Key）
    
    返回:
        配置信息
    """
    return {
        "code": 200,
        "message": "成功",
        "data": {
            "base_url": settings.OPENAI_BASE_URL,
            "api_key_configured": settings.OPENAI_API_KEY is not None,
            "api_key_length": len(settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else 0,
            "api_key_preview": (
                settings.OPENAI_API_KEY[:10] + "..." + settings.OPENAI_API_KEY[-4:]
                if settings.OPENAI_API_KEY and len(settings.OPENAI_API_KEY) > 14
                else "未配置"
            )
        }
    }
