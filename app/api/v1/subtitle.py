"""
字幕相关 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.subtitle import Subtitle
from app.schemas.subtitle import SubtitleUpdate, SubtitleResponse

router = APIRouter()


@router.put("/{subtitle_id}", response_model=SubtitleResponse)
def update_subtitle(
    subtitle_id: int,
    subtitle_in: SubtitleUpdate,
    db: Session = Depends(get_db)
):
    """
    更新字幕内容
    """
    subtitle = db.query(Subtitle).filter(Subtitle.id == subtitle_id).first()
    if not subtitle:
        raise HTTPException(status_code=404, detail="字幕不存在")
        
    # 验证时间轴（如果同时更新开始和结束时间）
    start_time = subtitle_in.start_time if subtitle_in.start_time is not None else subtitle.start_time
    end_time = subtitle_in.end_time if subtitle_in.end_time is not None else subtitle.end_time
    
    if start_time and end_time and start_time >= end_time:
        raise HTTPException(status_code=400, detail="结束时间必须大于开始时间")
        
    # 更新字段
    update_data = subtitle_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(subtitle, field, value)
        
    db.commit()
    db.refresh(subtitle)
    
    return subtitle


@router.delete("/{subtitle_id}")
def delete_subtitle(subtitle_id: int, db: Session = Depends(get_db)):
    """
    删除字幕
    """
    subtitle = db.query(Subtitle).filter(Subtitle.id == subtitle_id).first()
    if not subtitle:
        raise HTTPException(status_code=404, detail="字幕不存在")
        
    db.delete(subtitle)
    db.commit()
    
    return {"message": "删除成功"}
