import base64
import hashlib
import hmac
import json
import secrets
import time
from ..config import get_settings
from .common import require


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    value = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260000).hex()
    return f"{salt}:{value}"


def password_valid(password, encoded):
    return hmac.compare_digest(password_hash(password, encoded.split(":")[0]), encoded)


def b64(value):
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def issue(user):
    head = b64(b'{"alg":"HS256","typ":"JWT"}')
    body = b64(
        json.dumps(
            {"sub": user["id"], "exp": int(time.time()) + 28800, "iss": "sehat-grid", "aud": "pilot-v1"}
        ).encode()
    )
    signature = b64(
        hmac.new(get_settings().jwt_secret.encode(), f"{head}.{body}".encode(), hashlib.sha256).digest()
    )
    return f"{head}.{body}.{signature}"


def authenticate(s, authorization):
    try:
        head, body, signature = authorization.removeprefix("Bearer ").split(".")
        expected = b64(
            hmac.new(get_settings().jwt_secret.encode(), f"{head}.{body}".encode(), hashlib.sha256).digest()
        )
        claims = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        valid = hmac.compare_digest(signature, expected) and claims["exp"] > time.time()
        valid = valid and claims["iss"] == "sehat-grid" and claims["aud"] == "pilot-v1"
        user = s["users"].get(claims["sub"]) if valid else None
    except (ValueError, KeyError, TypeError):
        user = None
    require(user and user["active"], "UNAUTHENTICATED", "Sign in with an active demo account", 401)
    return user


def public_user(u):
    return {k: u[k] for k in ("id", "name", "role", "facility_ids", "active")}
