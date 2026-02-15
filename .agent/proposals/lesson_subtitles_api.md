# Lesson Subtitles API 提案

## 概述

为课程（Lesson）添加一个新的 API 接口，返回完整的字幕数据，包括：
- 原文（英文）
- 翻译（中文）
- 音标（IPA）
- 语法分析

## 需求分析

### 用户需求
用户需要获取课程的完整字幕数据，用于：
1. 前端播放器显示字幕
2. 展示翻译和音标
3. 显示语法分析结果
4. 支持学习功能（如点击单词查看详情）

### 数据来源
数据来自以下数据库表：
- `subtitles` - 字幕基础数据（原文、翻译、音标、时间轴）
- `grammar_analysis` - 语法分析数据（关联到 subtitle_id）

## API 设计

### 端点
```
GET /api/v1/lessons/{lesson_id}/subtitles
```

### 请求参数
- `lesson_id` (路径参数): Lesson ID

### 响应格式

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
    },
    {
      "sequence_number": 2,
      "start_time": 3.5,
      "end_time": 6.0,
      "original_text": "Litter baskets have been placed under the trees,",
      "translation": "垃圾篮已经放在了树下。",
      "phonetic": "/ˈlɪtər ˈbæskɪts hæv biːn pleɪst ˈʌndər ðə triːz,/",
      "grammar_analysis": []
    }
  ]
}
```

## Schema 设计

### 新增 Pydantic Schemas

```python
# app/schemas/subtitle.py

class GrammarAnalysisItem(BaseModel):
    """单个语法分析项"""
    word: str
    part_of_speech: str
    explanation: Optional[str] = None
    translation: Optional[str] = None
    
    class Config:
        from_attributes = True

class SubtitleDetailResponse(BaseModel):
    """单条字幕详细信息"""
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

## 实现步骤

### 1. 创建 Schema 文件
- 创建 `app/schemas/subtitle.py`
- 定义 `GrammarAnalysisItem`, `SubtitleDetailResponse`, `LessonSubtitlesResponse`

### 2. 实现 API 端点
- 在 `app/api/v1/lessons.py` 添加新端点
- 查询 Lesson → Video → Subtitles
- 关联查询 GrammarAnalysis
- 组装返回数据

### 3. 数据库查询优化
- 使用 `joinedload` 预加载关联数据
- 避免 N+1 查询问题

### 4. 错误处理
- Lesson 不存在 → 404
- Video 不存在 → 404
- 无字幕数据 → 返回空列表

## 技术考虑

### 性能优化
1. **数据库查询优化**
   - 使用 `joinedload` 一次性加载所有关联数据
   - 按 `sequence_number` 排序

2. **响应缓存**（可选，未来优化）
   - 字幕数据相对静态，可以考虑缓存
   - 使用 Redis 缓存完整响应

### 数据一致性
- 确保返回的字幕数据与视频处理完成后的数据一致
- 处理中的课程可能没有完整数据

### 扩展性
- 未来可以支持多语言字幕
- 可以添加过滤参数（如只返回某个时间段的字幕）

## 测试计划

### 单元测试
1. 测试正常情况 - 返回完整字幕数据
2. 测试 Lesson 不存在
3. 测试 Video 不存在
4. 测试无字幕数据
5. 测试语法分析数据关联

### 集成测试
1. 端到端测试完整流程
2. 验证数据格式正确性
3. 验证性能（大量字幕数据）

## 示例代码

```python
@router.get("/{lesson_id}/subtitles", response_model=LessonSubtitlesResponse)
def get_lesson_subtitles(lesson_id: int, db: Session = Depends(get_db)):
    """
    获取课程完整字幕数据（包括翻译、音标、语法分析）
    """
    # 查询 Lesson
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    if not lesson.video_id:
        raise HTTPException(status_code=404, detail="No video associated with this lesson")
    
    # 查询字幕，预加载语法分析
    subtitles = db.query(Subtitle).options(
        joinedload(Subtitle.grammar_analyses)
    ).filter(
        Subtitle.video_id == lesson.video_id
    ).order_by(Subtitle.sequence_number).all()
    
    # 组装响应数据
    subtitle_details = []
    for sub in subtitles:
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

## 时间估算

- Schema 设计和实现: 30 分钟
- API 端点实现: 1 小时
- 测试: 30 分钟
- 文档: 15 分钟

**总计**: 约 2 小时

## 风险和缓解

### 风险
1. 大量字幕数据可能导致响应过大
2. 语法分析数据可能不完整

### 缓解措施
1. 添加分页支持（可选）
2. 返回空列表而不是报错
3. 添加响应大小监控

## 后续优化

1. 添加分页支持
2. 支持时间范围过滤
3. 添加缓存层
4. 支持多语言字幕
5. 添加字幕搜索功能
