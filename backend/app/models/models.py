import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Upload(Base):
    __tablename__ = "uploads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename: Mapped[str] = mapped_column(String(512))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    session_count: Mapped[int] = mapped_column(Integer, default=0)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    parse_warnings: Mapped[list] = mapped_column(JSON, default=list)

    sessions: Mapped[list["Session"]] = relationship(back_populates="upload", cascade="all, delete-orphan")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    upload_id: Mapped[str] = mapped_column(ForeignKey("uploads.id", ondelete="CASCADE"), index=True)
    sid: Mapped[str] = mapped_column(String(128), index=True)
    call_id: Mapped[str | None] = mapped_column(String(512), index=True)
    from_header: Mapped[str | None] = mapped_column(String(512))
    to_header: Mapped[str | None] = mapped_column(String(512))
    first_timestamp: Mapped[str | None] = mapped_column(String(32))
    last_timestamp: Mapped[str | None] = mapped_column(String(32))
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    methods: Mapped[list] = mapped_column(JSON, default=list)

    upload: Mapped["Upload"] = relationship(back_populates="sessions")
    messages: Mapped[list["Message"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    timestamp: Mapped[str] = mapped_column(String(32))
    device_ip: Mapped[str] = mapped_column(String(64))
    severity: Mapped[str] = mapped_column(String(64))
    direction: Mapped[str | None] = mapped_column(String(16))
    peer_ip: Mapped[str | None] = mapped_column(String(64))
    peer_port: Mapped[int | None] = mapped_column(Integer)
    raw_text: Mapped[str] = mapped_column(Text)
    method: Mapped[str | None] = mapped_column(String(32), index=True)
    status_code: Mapped[int | None] = mapped_column(Integer)
    call_id: Mapped[str | None] = mapped_column(String(512))
    from_header: Mapped[str | None] = mapped_column(String(512))
    to_header: Mapped[str | None] = mapped_column(String(512))
    cseq: Mapped[str | None] = mapped_column(String(128))
    via: Mapped[str | None] = mapped_column(String(512))
    headers: Mapped[dict] = mapped_column(JSON, default=dict)
    body: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    session: Mapped["Session"] = relationship(back_populates="messages")
