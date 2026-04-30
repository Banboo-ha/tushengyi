from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api.admin.router import router as admin_router
from app.api.h5.router import router as h5_router
from app.config import BASE_DIR, UPLOAD_DIR, ensure_runtime_dirs
from app.db import Base, SessionLocal, engine
from app.services.settings import init_defaults


def create_app() -> FastAPI:
    ensure_runtime_dirs()
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        if engine.url.get_backend_name() == "sqlite":
            columns = {row[1] for row in conn.execute(text("PRAGMA table_info(poster_tasks)"))}
            if "image_quality" not in columns:
                conn.execute(text("ALTER TABLE poster_tasks ADD COLUMN image_quality VARCHAR(20) DEFAULT 'medium'"))
            if "poster_type" not in columns:
                conn.execute(text("ALTER TABLE poster_tasks ADD COLUMN poster_type VARCHAR(40) DEFAULT 'product'"))
    db = SessionLocal()
    try:
        init_defaults(db)
    finally:
        db.close()

    app = FastAPI(title="海报快生 MVP", version="0.1.0")
    app.include_router(h5_router)
    app.include_router(admin_router)
    app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
    app.mount("/h5-static", StaticFiles(directory=str(BASE_DIR / "app" / "static" / "h5")), name="h5-static")
    app.mount("/admin-static", StaticFiles(directory=str(BASE_DIR / "app" / "static" / "admin")), name="admin-static")

    @app.get("/")
    def root():
        return RedirectResponse("/h5")

    @app.get("/h5")
    def h5_app():
        return FileResponse(BASE_DIR / "app" / "static" / "h5" / "index.html")

    @app.get("/admin")
    def admin_app():
        return FileResponse(BASE_DIR / "app" / "static" / "admin" / "index.html")

    @app.get("/healthz")
    def healthz():
        return {"ok": True, "service": "haibaokuaisheng"}

    @app.get("/readyz")
    def readyz():
        db = SessionLocal()
        try:
            db.execute(text("select 1"))
            return {"ok": True, "database": "ok"}
        finally:
            db.close()

    return app


app = create_app()
