import logging
import signal
import time

from app.config import WORKER_BATCH_SIZE, WORKER_POLL_SECONDS
from app.db import Base, engine
from app.services.poster import process_next_tasks, reset_stale_running_tasks
from app.services.settings import init_defaults
from app.db import SessionLocal


logger = logging.getLogger(__name__)
_running = True


def _stop(signum, frame):
    global _running
    _running = False
    logger.info("worker received stop signal %s", signum)


def run_worker() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        init_defaults(db)
    finally:
        db.close()

    reset_count = reset_stale_running_tasks()
    if reset_count:
        logger.info("reset %s stale running tasks", reset_count)

    logger.info("poster worker started")
    while _running:
        processed = process_next_tasks(limit=WORKER_BATCH_SIZE)
        if processed == 0:
            time.sleep(WORKER_POLL_SECONDS)
    logger.info("poster worker stopped")

