from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "live_train_tracker",
    broker = settings.REDIS_URL,
    include = ["app.tasks"],
)

