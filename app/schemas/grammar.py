"""
语法分析 Pydantic 模型
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.subtitle import SubtitleResponse


class GrammarAnalysisBase(BaseModel):
    sentence_structure: Optional[str] = None
    grammar_points: Optional[List[str]] = None
    difficult_words: Optional[List[Dict[str, Any]]] = None
    phrases: Optional[List[str]] = None
    explanation: Optional[str] = None


class GrammarAnalysisResponse(GrammarAnalysisBase):
    id: int
    subtitle_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SubtitleWithGrammarResponse(SubtitleResponse):
    grammar_analysis: Optional[GrammarAnalysisResponse] = None
