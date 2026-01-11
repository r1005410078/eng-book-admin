from app.core.celery_app import celery_app
from app.core.config import settings

print(f"Broker URL: {settings.CELERY_BROKER_URL or settings.REDIS_URL}")
print(f"Backend URL: {settings.CELERY_RESULT_BACKEND or settings.CELERY_BROKER_URL or settings.REDIS_URL}")

try:
    with celery_app.connection() as conn:
        print("Connection successful!")
        print(f"Connected to: {conn.as_uri()}")
        try:
            conn.default_channel.ping()
            print("Ping successful!")
        except Exception as e:
            print(f"Ping failed: {e}")
except Exception as e:
    print(f"Connection failed: {e}")
