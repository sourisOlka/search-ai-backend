import asyncio
import os
from celery import Celery

REDIS_URL = os.environ.get("REDIS_URL")


celery_app = Celery(
    "backend_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["src.tasks.files"] 
)

def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)