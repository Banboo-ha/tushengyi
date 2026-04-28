from fastapi import APIRouter

from app.api.h5 import auth, points, poster, upload, user, works

router = APIRouter(prefix="/api/h5")
router.include_router(auth.router)
router.include_router(user.router)
router.include_router(upload.router)
router.include_router(poster.router)
router.include_router(works.router)
router.include_router(points.router)

