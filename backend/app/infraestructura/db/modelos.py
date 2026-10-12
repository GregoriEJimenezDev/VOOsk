"""Modelos SQLAlchemy (PostgreSQL)."""
from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _ahora():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    creado: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ahora)

    proyectos: Mapped[list["Project"]] = relationship(back_populates="owner", cascade="all,delete")
    credenciales: Mapped[list["Credential"]] = relationship(back_populates="owner", cascade="all,delete")


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    nombre: Mapped[str] = mapped_column(String(200))
    descripcion: Mapped[str] = mapped_column(Text, default="")
    ruta: Mapped[str] = mapped_column(Text, default="")  # carpeta de trabajo del proyecto
    creado: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ahora)

    owner: Mapped[User] = relationship(back_populates="proyectos")
    tareas: Mapped[list["TaskSession"]] = relationship(back_populates="proyecto", cascade="all,delete")


class Credential(Base):
    """Credencial BYOK o gratuita. El secreto SIEMPRE cifrado (Fernet). Nunca en logs."""
    __tablename__ = "credentials"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    proveedor: Mapped[str] = mapped_column(String(50))  # groq | ollama | openai | anthropic
    etiqueta: Mapped[str] = mapped_column(String(200), default="")
    secreto_cifrado: Mapped[str] = mapped_column(Text, default="")  # "" = modelo gratuito sin key
    creado: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ahora)

    owner: Mapped[User] = relationship(back_populates="credenciales")


class TaskSession(Base):
    __tablename__ = "task_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    objetivo: Mapped[str] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(String(30), default="pendiente")
    modelo: Mapped[str] = mapped_column(String(50), default="gratuito")
    resumen: Mapped[str] = mapped_column(Text, default="")
    ruta: Mapped[str] = mapped_column(Text, default="")  # carpeta donde genera archivos
    creado: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ahora)

    proyecto: Mapped[Project | None] = relationship(back_populates="tareas")
    eventos: Mapped[list["TaskEvent"]] = relationship(back_populates="sesion", cascade="all,delete",
                                                      order_by="TaskEvent.id")


class TaskEvent(Base):
    __tablename__ = "task_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("task_sessions.id", ondelete="CASCADE"), index=True)
    tipo: Mapped[str] = mapped_column(String(50), index=True)
    datos: Mapped[dict] = mapped_column(JSON, default=dict)
    creado: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_ahora)

    sesion: Mapped[TaskSession] = relationship(back_populates="eventos")
