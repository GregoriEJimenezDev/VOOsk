"""Cifrado Fernet para credenciales BYOK en reposo. Nunca loguear el secreto."""
from cryptography.fernet import Fernet
from app.config import settings

_clave = settings.FERNET_KEY.encode() if settings.FERNET_KEY else Fernet.generate_key()
_fernet = Fernet(_clave)

def cifrar(secreto: str) -> str:
    return _fernet.encrypt(secreto.encode()).decode()

def descifrar(token: str) -> str:
    if not token:
        return ""
    return _fernet.decrypt(token.encode()).decode()
