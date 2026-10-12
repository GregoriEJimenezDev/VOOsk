import os

# Carga backend/.env (si existe) en las variables de entorno.
# Sin esto, el .env del README nunca se leería.
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
except ImportError:
    pass


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+psycopg://ia:ia@localhost:5432/ia_transparente")
    JWT_SECRET: str = os.getenv("JWT_SECRET", "cambia-este-secreto-en-produccion")
    JWT_ALG: str = "HS256"
    JWT_MINUTOS: int = int(os.getenv("JWT_MINUTOS", "720"))
    FERNET_KEY: str = os.getenv("FERNET_KEY", "")  # si vacío se genera efímera (ver seguridad/crypto)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.1")
    WORKSPACE: str = os.getenv("WORKSPACE", "./workspace")
    CORS_ORIGINS: list[str] = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")]
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5174")
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    GOOGLE_REDIRECT: str = os.getenv("GOOGLE_REDIRECT", "http://localhost:8000/auth/google/callback")

settings = Settings()
