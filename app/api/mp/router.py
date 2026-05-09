from fastapi import APIRouter

from app.api.h5 import points, poster, upload, works
from app.api.mp import auth, pay, user

router = APIRouter(prefix="/api/mp")
router.include_router(auth.router)
router.include_router(user.router)
router.include_router(upload.router)
router.include_router(poster.router)
router.include_router(works.router)
router.include_router(points.router)
router.include_router(pay.router)
