from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.services.ids import new_id


def now() -> datetime:
    return datetime.utcnow()


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    avatar: Mapped[str] = mapped_column(String(255), default="")
    points_balance: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="normal")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class Admin(Base):
    __tablename__ = "admins"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="normal")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class UploadedImage(Base):
    __tablename__ = "uploaded_images"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(32), index=True)
    image_url: Mapped[str] = mapped_column(String(512))
    storage_path: Mapped[str] = mapped_column(String(512))
    image_type: Mapped[str] = mapped_column(String(20))
    reference_type: Mapped[str] = mapped_column(String(40), default="")
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    width: Mapped[int] = mapped_column(Integer, default=0)
    height: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class PosterTask(Base):
    __tablename__ = "poster_tasks"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(32), index=True)
    task_type: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    product_image_ids: Mapped[str] = mapped_column(Text, default="[]")
    reference_image_ids: Mapped[str] = mapped_column(Text, default="[]")
    title: Mapped[str] = mapped_column(String(120), default="")
    subtitle: Mapped[str] = mapped_column(String(160), default="")
    selling_points: Mapped[str] = mapped_column(Text, default="")
    style: Mapped[str] = mapped_column(String(80), default="")
    ratio: Mapped[str] = mapped_column(String(20), default="3:4")
    edit_instruction: Mapped[str] = mapped_column(Text, default="")
    points_cost: Mapped[int] = mapped_column(Integer, default=0)
    prompt: Mapped[str] = mapped_column(Text, default="")
    result_image_url: Mapped[str] = mapped_column(String(512), default="")
    error_message: Mapped[str] = mapped_column(Text, default="")
    work_id: Mapped[str] = mapped_column(String(32), default="")
    version_id: Mapped[str] = mapped_column(String(32), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class PosterWork(Base):
    __tablename__ = "poster_works"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(120), default="")
    cover_url: Mapped[str] = mapped_column(String(512), default="")
    latest_version: Mapped[int] = mapped_column(Integer, default=1)
    is_saved: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)


class PosterVersion(Base):
    __tablename__ = "poster_versions"
    __table_args__ = (UniqueConstraint("work_id", "version_no", name="uq_work_version"),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    work_id: Mapped[str] = mapped_column(String(32), index=True)
    task_id: Mapped[str] = mapped_column(String(32), index=True)
    version_no: Mapped[int] = mapped_column(Integer)
    image_url: Mapped[str] = mapped_column(String(512))
    edit_instruction: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class PointsRecord(Base):
    __tablename__ = "points_records"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(32), index=True)
    type: Mapped[str] = mapped_column(String(20))
    amount: Mapped[int] = mapped_column(Integer)
    scene: Mapped[str] = mapped_column(String(80))
    related_id: Mapped[str] = mapped_column(String(32), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)

