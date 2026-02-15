# 课程字幕 API 规范

## 概述

添加新的 API 端点，用于获取课程的完整字幕数据，包括：
- 原文（英文）
- 翻译（中文）
- 音标（IPA）
- 语法分析

## API 端点

### GET /api/v1/lessons/{lesson_id}/subtitles

返回包含翻译、音标和语法分析的完整字幕数据。

#### 路径参数
- `lesson_id` (整数，必需): 课程 ID

#### 响应格式

```json
{
  "lesson_id": 70,
  "video_id": 89,
  "subtitle_count": 32,
  "subtitles": [
    {
      "sequence_number": 1,
      "start_time": 0.0,
      "end_time": 3.5,
      "original_text": "Visitors have been asked to keep the woods clean and tidy.",
      "translation": "游客被要求保持森林的清洁和整洁。",
      "phonetic": "ˈvɪzɪtərz hæv biːn æskt tuː kiːp ðə wʊdz kliːn ænd ˈtaɪdi.",
      "grammar_analysis": [
        {
          "word": "Visitors",
          "part_of_speech": "noun",
          "explanation": "主语，复数名词",
          "translation": "游客"
        },
        {
          "word": "have been asked",
          "part_of_speech": "verb_phrase",
          "explanation": "现在完成时被动语态",
          "translation": "被要求"
        }
      ]
    }
  ]
}
```

#### 错误响应

- `404 Not Found`: 课程不存在
- `404 Not Found`: 该课程没有关联的视频

## 数据模型

### Pydantic Schemas

创建新文件: `app/schemas/subtitle.py`

```python
from typing import List, Optional
from pydantic import BaseModel

class GrammarAnalysisItem(BaseModel):
    """单个语法分析项"""
    word: str
    part_of_speech: str
    explanation: Optional[str] = None
    translation: Optional[str] = None
    
    class Config:
        from_attributes = True

class SubtitleDetailResponse(BaseModel):
    """字幕详细信息"""
    sequence_number: int
    start_time: float
    end_time: float
    original_text: str
    translation: Optional[str] = None
    phonetic: Optional[str] = None
    grammar_analysis: List[GrammarAnalysisItem] = []
    
    class Config:
        from_attributes = True

class LessonSubtitlesResponse(BaseModel):
    """课程完整字幕数据"""
    lesson_id: int
    video_id: int
    subtitle_count: int
    subtitles: List[SubtitleDetailResponse]
```

## 数据库查询

### 查询策略

1. 根据 ID 查询 Lesson
2. 验证 Video 存在
3. 使用 `joinedload` 查询 Subtitles 及关联的 GrammarAnalysis
4. 按 sequence_number 排序

### 性能优化

- 使用 SQLAlchemy 的 `joinedload` 避免 N+1 查询
- 单次数据库查询获取所有关联数据
- 在 `video_id` 和 `sequence_number` 上建立适当索引

## 实现

### 文件: app/api/v1/lessons.py

添加新端点:

```python
from sqlalchemy.orm import joinedload
from app.schemas.subtitle import (
    LessonSubtitlesResponse,
    SubtitleDetailResponse,
    GrammarAnalysisItem
)
from app.models.grammar import GrammarAnalysis

@router.get("/{lesson_id}/subtitles", response_model=LessonSubtitlesResponse)
def get_lesson_subtitles(lesson_id: int, db: Session = Depends(get_db)):
    """
    获取课程的完整字幕数据
    包括翻译、音标和语法分析
    """
    # 查询课程
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    if not lesson.video_id:
        raise HTTPException(
            status_code=404, 
            detail="No video associated with this lesson"
        )
    
    # 查询字幕，预加载语法分析
    subtitles = db.query(Subtitle).options(
        joinedload(Subtitle.grammar_analyses)
    ).filter(
        Subtitle.video_id == lesson.video_id
    ).order_by(Subtitle.sequence_number).all()
    
    # 构建响应
    subtitle_details = []
    for sub in subtitles:
        # 提取语法分析
        grammar_items = [
            GrammarAnalysisItem(
                word=ga.word,
                part_of_speech=ga.part_of_speech,
                explanation=ga.explanation,
                translation=ga.translation
            )
            for ga in sub.grammar_analyses
        ]
        
        subtitle_details.append(SubtitleDetailResponse(
            sequence_number=sub.sequence_number,
            start_time=sub.start_time,
            end_time=sub.end_time,
            original_text=sub.original_text,
            translation=sub.translation,
            phonetic=sub.phonetic,
            grammar_analysis=grammar_items
        ))
    
    return LessonSubtitlesResponse(
        lesson_id=lesson.id,
        video_id=lesson.video_id,
        subtitle_count=len(subtitle_details),
        subtitles=subtitle_details
    )
```

## 测试

### 测试用例

1. **成功场景**: 返回完整字幕数据
2. **课程不存在**: 返回 404
3. **无视频**: 返回 404
4. **空字幕**: 返回空列表
5. **语法分析**: 验证正确关联

### 测试文件: tests/api/v1/test_lessons_subtitles.py

```python
def test_get_lesson_subtitles_success(client, db_session):
    """测试成功获取字幕数据"""
    # 创建测试数据
    lesson = create_test_lesson_with_subtitles(db_session)
    
    response = client.get(f"/api/v1/lessons/{lesson.id}/subtitles")
    
    assert response.status_code == 200
    data = response.json()
    assert data["lesson_id"] == lesson.id
    assert data["subtitle_count"] > 0
    assert len(data["subtitles"]) > 0
    
    # 验证字幕结构
    subtitle = data["subtitles"][0]
    assert "sequence_number" in subtitle
    assert "original_text" in subtitle
    assert "translation" in subtitle
    assert "phonetic" in subtitle
    assert "grammar_analysis" in subtitle

def test_get_lesson_subtitles_not_found(client):
    """测试课程不存在时返回 404"""
    response = client.get("/api/v1/lessons/99999/subtitles")
    assert response.status_code == 404
```

## 依赖

### 数据库模型
- `Lesson` (app/models/course.py)
- `Video` (app/models/video.py)
- `Subtitle` (app/models/subtitle.py)
- `GrammarAnalysis` (app/models/grammar.py)

### 必需的关系
确保 `Subtitle` 模型有到 `GrammarAnalysis` 的关系:

```python
# 在 app/models/subtitle.py 中
grammar_analyses = relationship("GrammarAnalysis", back_populates="subtitle")
```

## 未来增强

1. **分页**: 为大量字幕集添加 limit/offset 参数
2. **时间范围过滤**: 按时间范围过滤字幕
3. **缓存**: 在 Redis 中缓存响应
4. **多语言**: 支持多种字幕语言
5. **搜索**: 在字幕中添加全文搜索

## 验收标准

- [ ] 创建新的 schema 文件: `app/schemas/subtitle.py`
- [ ] 添加新端点: `GET /api/v1/lessons/{lesson_id}/subtitles`
- [ ] 返回包含所有字段的完整字幕数据
- [ ] 语法分析正确关联
- [ ] 处理缺失课程/视频的错误
- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] API 文档已更新
