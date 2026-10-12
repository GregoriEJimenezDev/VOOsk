from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.infraestructura.db.modelos import Base

# SQLite se usa en hilos distintos (FastAPI opera en threadpool):
# hay que relajar check_same_thread.
_kwargs = ({"connect_args": {"check_same_thread": False}}
           if settings.DATABASE_URL.startswith("sqlite") else {})
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True, **_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def crear_tablas():
    Base.metadata.create_all(bind=engine)
    migrar()

def migrar():
    """Migración ligera: añade columnas nuevas a BD ya existentes (SQLite y PG)."""
    for tabla, col in (("projects", "ruta"), ("task_sessions", "ruta")):
        try:
            with engine.begin() as c:
                if engine.dialect.name == "postgresql":
                    c.execute(text(f"ALTER TABLE {tabla} ADD COLUMN IF NOT EXISTS {col} TEXT DEFAULT ''"))
                else:
                    cols = [r[1] for r in c.execute(text(f"PRAGMA table_info({tabla})")).fetchall()]
                    if col not in cols:
                        c.execute(text(f"ALTER TABLE {tabla} ADD COLUMN {col} TEXT DEFAULT ''"))
        except Exception:
            pass  # la columna ya existe o la tabla aún no se crea

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
