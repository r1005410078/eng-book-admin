from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status, BackgroundTasks, Header
from sqlalchemy.orm import Session
from app.core.database import get_db, SessionLocal
from app.models.course import Course, Unit, Lesson
from app.models.task_journal import TaskJournal
from app.models.video import Video, VideoStatus
from app.schemas.course import CourseResponse, CourseProgressResponse, LessonProgressResponse, TaskJournalResponse
from app.tasks.course_tasks import process_course_lesson
from app.utils.file_handler import file_handler
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging

# Set up logger
logger = logging.getLogger(__name__)

router = APIRouter()

# Global thread pool for I/O operations
io_executor = ThreadPoolExecutor(max_workers=4)

def _save_file_task(file, video_id: int, filename: str):
    """
    Synchronous task to save file using shutil.copyfileobj
    """
    file_handler.save_file_stream(file.file, video_id, filename)

def _background_create_records(course_id: int, file_records: List[dict]):
    """
    Background DB record creation and Celery triggering.
    Executed AFTER file persistence.
    """
    print(f"🔥🔥🔥 _background_create_records CALLED for Course {course_id} 🔥🔥🔥")
    logger.warning(f"🔥 _background_create_records STARTED for Course {course_id}, file_records count: {len(file_records)}")
    
    db = SessionLocal()
    try:
        logger.info(f"Creating DB records for Course {course_id}, Count: {len(file_records)}")
        
        for record in file_records:
            try:
                filename = record['filename']
                video_id = record['video_id']
                unit_id = record['unit_id']  # Get unit_id from record
                file_size = record['file_size']
                saved_path = record['saved_path']
                idx = record['index']
                
                # Fetch placeholder video
                video = db.query(Video).filter(Video.id == video_id).first()
                if video:
                    video.file_path = saved_path
                    video.file_size = file_size
                    video.status = VideoStatus.UPLOADING # Will be updated by task
                
                # Create Lesson
                safe_title = filename[:255] if filename else f"Lesson {idx}"
                new_lesson = Lesson(
                    unit_id=unit_id,
                    title=safe_title,
                    order_index=idx,
                    video_id=video_id,
                    processing_status="PENDING",
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                db.add(new_lesson)
                db.flush() 
                
                # Init Journal
                journal = TaskJournal(
                    lesson_id=new_lesson.id,
                    step_name="INIT",
                    action="COMPLETE",
                    context={"filename": filename, "video_id": video_id},
                    created_at=datetime.now()
                )
                db.add(journal)
                db.commit()
                
                logger.info(f"About to trigger Celery task for Lesson {new_lesson.id}")
                try:
                    processing_task = process_course_lesson.delay(new_lesson.id)
                    logger.info(f"✅ Triggered task {processing_task.id} for Lesson {new_lesson.id}")
                except Exception as celery_error:
                    logger.error(f"❌ Failed to trigger Celery task for Lesson {new_lesson.id}: {celery_error}")
                    logger.exception(celery_error)
                
            except Exception as e:
                logger.error(f"Error creating DB record for {filename}: {e}")
                logger.exception(e)
                db.rollback()
                continue
                
    except Exception as e:
        logger.error(f"Background DB Creation Error: {e}")
    finally:
        db.close()


@router.post("/upload", response_model=CourseResponse)
async def upload_course(
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    description: str = Form(None),
    level: str = Form(None),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    流式异步上传流程 (Streaming Async Upload):
    1. 创建课程结构 (Course & Unit)
    2. 创建 Video 做占位符
    3. 异步流式保存文件到磁盘 (Non-blocking I/O via ThreadPool) - 不占用 RAM
    4. 收集保存结果
    5. 后台任务：完善 DB 记录并触发 Celery 处理
    """
    # Create Course first
    new_course = Course(
        title=title,
        description=description, 
        level=level, 
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    db.add(new_course)
    db.flush()
    db.commit()
    db.refresh(new_course)

    if not files:
        logger.warning("No files received in upload request")
        return new_course
        
    logger.info(f"Received {len(files)} files for upload")
    
    file_records = []
    loop = asyncio.get_running_loop()
    
    for idx, file in enumerate(files):
        filename = file.filename or f"Lesson {idx+1}.mp4"
        safe_title = filename[:255]
        
        # 1. Create Unit for EACH file
        new_unit = Unit(
            course_id=new_course.id,
            title=safe_title, # Unit title same as file/lesson
            order_index=idx,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        db.add(new_unit)
        db.commit()
        db.refresh(new_unit)
        
        # 2. Create Video Placeholder
        new_video = Video(
            title=safe_title,
            description=f"Auto-generated for Course {new_course.id}",
            file_path="",  # Will be updated
            status=VideoStatus.UPLOADING,
            created_at=datetime.now()
        )
        db.add(new_video)
        db.commit() # Commit to get ID
        db.refresh(new_video)
        
        # 3. Stream Save to Disk (Offload to thread pool avoid blocking loop)
        logger.info(f"Streaming file {idx+1}: {filename}")
        
        saved_path = await loop.run_in_executor(
            io_executor,
            file_handler.save_file_stream,
            file.file, 
            new_video.id, 
            filename
        )
        
        # Get actual file size from disk after save
        full_path = file_handler.get_file_path(saved_path)
        file_size = file_handler.get_file_size(full_path)
        
        file_records.append({
            "filename": filename,
            "video_id": new_video.id,
            "unit_id": new_unit.id,
            "saved_path": saved_path,
            "file_size": file_size,
            "index": idx
        })

    # 3. Add to Background Tasks for finalizing DB and triggering Celery
    background_tasks.add_task(
        _background_create_records,
        new_course.id,
        file_records
    )
    
    return new_course

@router.get("/{course_id}/progress", response_model=CourseProgressResponse)
def get_course_progress(course_id: int, db: Session = Depends(get_db)):
    """
    统一进度查询：
    返回该课程下所有课时的处理状态及详细日志
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    lessons_progress = []
    # Join Unit to get lessons
    units = db.query(Unit).filter(Unit.course_id == course_id).all()
    for unit in units:
        lessons = db.query(Lesson).filter(Lesson.unit_id == unit.id).all()
        for lesson in lessons:
            logs = db.query(TaskJournal).filter(TaskJournal.lesson_id == lesson.id).order_by(TaskJournal.created_at.desc()).all()
            log_responses = [TaskJournalResponse.model_validate(log) for log in logs]
            
            lessons_progress.append(LessonProgressResponse(
                lesson_id=lesson.id,
                processing_status=lesson.processing_status,
                progress_percent=lesson.progress_percent,
                logs=log_responses
            ))
            
    return CourseProgressResponse(
        course_id=course.id,
        lessons=lessons_progress
    )

@router.get("/{course_id}", response_model=CourseResponse)
def get_course(course_id: int, db: Session = Depends(get_db)):
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course

@router.patch("/{course_id}", response_model=CourseResponse)
def modify_course(course_id: int, title: str = Form(None), description: str = Form(None), db: Session = Depends(get_db)):
    # Simple modify implementation
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    if title:
        course.title = title
    if description:
        course.description = description
    
    course.updated_at = datetime.now()
    db.commit()
    db.refresh(course)
    return course

@router.get("", response_model=List[CourseResponse], summary="获取课程列表")
def get_courses(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    获取所有课程列表 (支持分页)
    """
    courses = db.query(Course).order_by(Course.created_at.desc()).offset(skip).limit(limit).all()
    return courses

from app.models.user_course import UserCourse

@router.post("/{course_id}/join", summary="加入/切换课程")
def join_course(
    course_id: int,
    x_user_id: int = Header(..., description="User ID"),
    db: Session = Depends(get_db)
):
    """
    用户加入或切换到指定课程。
    会将其设置为当前激活课程 (is_active=True)，并将该用户其他课程设为 inactive。
    """
    # Verify course exists
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    try:
        # 1. Set all enrollments for this user to inactive
        db.query(UserCourse).filter(UserCourse.user_id == x_user_id).update({"is_active": False})
        
        # 2. Check existing enrollment
        enrollment = db.query(UserCourse).filter(
            UserCourse.user_id == x_user_id,
            UserCourse.course_id == course_id
        ).first()
        
        if enrollment:
            enrollment.is_active = True
            enrollment.last_accessed_at = datetime.now()
        else:
            enrollment = UserCourse(
                user_id=x_user_id,
                course_id=course_id,
                is_active=True,
                joined_at=datetime.now(),
                last_accessed_at=datetime.now()
            )
            db.add(enrollment)
            
        db.commit()
        return {"message": "Joined course successfully", "course_id": course_id}
        
    except Exception as e:
        db.rollback()
        logger.error(f"Join course failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

from fastapi import Header
from app.schemas.learning import LearningStatusResponse
from app.services.learning_service import LearningService

@router.get("/{course_id}/learning-status", response_model=LearningStatusResponse, summary="获取学习状态")
def get_learning_status(
    course_id: int,
    x_user_id: int = Header(..., description="用户ID (Mock Auth)"),
    db: Session = Depends(get_db)
):
    """
    获取当前用户在该课程的学习状态概览
    """
    service = LearningService(db)
    # Validate course
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
        
    return service.get_course_learning_status(user_id=x_user_id, course_id=course_id)
