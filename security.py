import hashlib, hmac, os, time
from . import config

ITER = 200_000


def hash_password(pw: str) -> str:
    salt = os.urandom(16)
    h = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, ITER)
    return f"{salt.hex()}${h.hex()}"


def verify_password(pw: str, stored: str) -> bool:
    try:
        salt, h = stored.split("$")
    except ValueError:
        return False
    new = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), ITER)
    return hmac.compare_digest(new.hex(), h)


def _sig(msg: str) -> str:
    return hmac.new(config.SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest()


def make_token(uid: int, ttl: int = 7 * 86400) -> str:
    body = f"{uid}.{int(time.time()) + ttl}"
    return f"{body}.{_sig(body)}"


def read_token(token: str | None):
    try:
        uid, exp, sig = (token or "").split(".")
        if hmac.compare_digest(sig, _sig(f"{uid}.{exp}")) and int(exp) > time.time():
            return int(uid)
    except ValueError:
        pass
    return None


_hits: dict[str, list[float]] = {}


def too_many(key: str, limit: int = 5, window: int = 300) -> bool:
    """Yaddaşda giriş cəhdi limiti (bir proses üçün)."""
    now = time.time()
    h = [t for t in _hits.get(key, []) if now - t < window]
    h.append(now)
    _hits[key] = h
    return len(h) > limit
