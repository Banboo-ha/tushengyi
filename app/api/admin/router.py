from fastapi import APIRouter

from app.api.admin import auth, points, settings, tasks, users, works

router = APIRouter(prefix="/api/admin")
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(tasks.router)
router.include_router(works.router)
router.include_router(points.router)
router.include_router(settings.router)

