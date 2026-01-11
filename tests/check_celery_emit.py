from app.core.celery_app import celery_app
from celery.result import AsyncResult
import time

print("Testing Celery task submission...")

try:
    # 我们可以尝试发送一个不存在的任务，或者定义一个简单的测试任务
    # 但我们没有简单的测试任务。
    # 我们直接尝试发送 process_uploaded_video，给一个不存在的 video_id，预期它会被发送，然后 worker 执行时报错（或者入队成功）。
    # 我们只关心发送是否成功。
    
    # 使用 send_task 绕过 import 问题
    print("Sending task...")
    result = celery_app.send_task("app.tasks.video_tasks.process_uploaded_video", args=[999999])
    print(f"Task sent! ID: {result.id}")
    print(f"Task state: {result.state}")
    
    # 检查 backend 连接
    print("Checking backend...")
    try:
        # 尝试访问 result 以触发 backend 连接
        _ = result.status
        print("Backend access successful.")
    except Exception as e:
        print(f"Backend access expectedly failed or skipped: {e}")

except Exception as e:
    print(f"FAILED: {e}")
    import traceback
    traceback.print_exc()
