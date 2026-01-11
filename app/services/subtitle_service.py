"""
字幕业务逻辑服务
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload

from app.models.subtitle import Subtitle
from app.models.grammar_analysis import GrammarAnalysis
from app.schemas.subtitle import SubtitleCreate, SubtitleUpdate


class SubtitleService:
    @staticmethod
    def get_by_video_id(
        db: Session,
        video_id: int,
        include_grammar: bool = False
    ) -> List[Subtitle]:
        """获取视频的所有字幕"""
        query = db.query(Subtitle).filter(Subtitle.video_id == video_id)
        
        if include_grammar:
            query = query.options(joinedload(Subtitle.grammar_analysis))
            
        return query.order_by(Subtitle.sequence_number).all()

    @staticmethod
    def get(db: Session, subtitle_id: int) -> Optional[Subtitle]:
        """获取单个字幕"""
        return db.query(Subtitle).filter(Subtitle.id == subtitle_id).first()

    @staticmethod
    def update(db: Session, db_obj: Subtitle, obj_in: SubtitleUpdate) -> Subtitle:
        """更新字幕"""
        update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
            
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    @staticmethod
    def delete(db: Session, subtitle_id: int) -> bool:
        """删除字幕"""
        obj = db.query(Subtitle).filter(Subtitle.id == subtitle_id).first()
        if not obj:
            return False
            
        db.delete(obj)
        db.commit()
        return True
        
    @staticmethod
    def delete_by_video_id(db: Session, video_id: int):
        """删除视频的所有字幕"""
        db.query(Subtitle).filter(Subtitle.video_id == video_id).delete()
        db.commit()


subtitle_service = SubtitleService()
