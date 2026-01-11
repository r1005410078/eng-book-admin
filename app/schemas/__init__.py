"""
Pydantic模型模块
"""
from app.schemas.video import VideoCreate, VideoUpdate, VideoResponse, VideoListResponse
from app.schemas.subtitle import SubtitleCreate, SubtitleUpdate, SubtitleResponse, ProcessingTaskResponse
from app.schemas.grammar import GrammarAnalysisResponse, SubtitleWithGrammarResponse

__all__ = [
    "VideoCreate", "VideoUpdate", "VideoResponse", "VideoListResponse",
    "SubtitleCreate", "SubtitleUpdate", "SubtitleResponse", "ProcessingTaskResponse",
    "GrammarAnalysisResponse", "SubtitleWithGrammarResponse"
]
