"""Hash de passwords (pbkdf2, sin dependencias nativas problemáticas)."""
import hashlib, hmac, os

def hash_password(password: str) -> str:
    sal = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), sal, 200_000)
    return f"pbkdf2${sal.hex()}${dk.hex()}"

def verificar_password(password: str, guardado: str) -> bool:
    try:
        _, sal_hex, dk_hex = guardado.split("$")
        dk2 = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(sal_hex), 200_000)
        return hmac.compare_digest(dk2.hex(), dk_hex)
    except Exception:
        return False
