from app.core.database import SessionLocal
from app.models.processing_task import ProcessingTask

db = SessionLocal()
tasks = db.query(ProcessingTask).order_by(ProcessingTask.id.desc()).limit(5).all()
for t in tasks:
    print(f"Task ID: {t.id}, Video ID: {t.video_id}, Type: {t.task_type}, Status: {t.status}")
    if t.error_message:
        print(f"  Error: {t.error_message}")
db.close()
