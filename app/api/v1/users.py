from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user_course import UserCourse
from app.models.course import Course
from app.schemas.course import CourseResponse

router = APIRouter()

@router.get("/current-course", response_model=CourseResponse, summary="获取当前正在学习的课程")
def get_current_course(
    x_user_id: int = Header(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """
    获取用户当前激活的学习课程
    """
    enrollment = db.query(UserCourse).filter(
        UserCourse.user_id == x_user_id,
        UserCourse.is_active == True
    ).first()
    
    if not enrollment:
        raise HTTPException(status_code=404, detail="No active course found")
        
    course = db.query(Course).filter(Course.id == enrollment.course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    return course
