"""JWT minting/verification (RS256 + JWKS), modeled on the ERP-2.0 auth-service."""

import hashlib
import os
import secrets

import jwt
from django.conf import settings
from django.utils import timezone

from .models import BlacklistedToken, RefreshToken, User

_PRIVATE_KEY = None
_PUBLIC_KEY = None


def _load_keys():
    global _PRIVATE_KEY, _PUBLIC_KEY
    if _PRIVATE_KEY is not None:
        return _PRIVATE_KEY, _PUBLIC_KEY

    def _read(path):
        if path and os.path.exists(path):
            with open(path, "rb") as f:
                return f.read()
        return None

    priv = _read(settings.JWT_PRIVATE_KEY_PATH)
    pub = _read(settings.JWT_PUBLIC_KEY_PATH)
    if priv and pub:
        _PRIVATE_KEY, _PUBLIC_KEY = priv, pub
        return _PRIVATE_KEY, _PUBLIC_KEY

    # Ephemeral in-memory keypair so the app runs without key files in dev.
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    _PRIVATE_KEY = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    _PUBLIC_KEY = key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return _PRIVATE_KEY, _PUBLIC_KEY


def get_public_key_pem() -> bytes:
    _, pub = _load_keys()
    return pub


def effective_permissions_for(user) -> list:
    if user.is_super_admin:
        from permissions.models import Permission

        return list(Permission.objects.values_list("codename", flat=True))
    from permissions.models import EmployeeRole

    return list(
        EmployeeRole.objects.filter(user_id=user.id, role__is_active=True)
        .values_list("role__permissions__codename", flat=True)
        .distinct()
    )


def roles_for(user) -> list:
    from permissions.models import EmployeeRole

    roles = list(
        EmployeeRole.objects.filter(user_id=user.id, role__is_active=True).values_list("role__name", flat=True)
    )
    if user.is_super_admin and "Super Admin" not in roles:
        roles.append("Super Admin")
    return roles


def mint_access_token(user) -> str:
    priv, _ = _load_keys()
    now = timezone.now()
    payload = {
        "sub": str(user.id),
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "employee_id": user.employee.employee_code if user.employee_id else None,
        "is_super_admin": user.is_super_admin,
        "is_active": user.is_active,
        "roles": roles_for(user),
        "perms": effective_permissions_for(user),
        "token_type": "access",
        "iat": int(now.timestamp()),
        "exp": now + timezone.timedelta(hours=settings.ACCESS_TOKEN_EXPIRY_HOURS),
        "iss": "fct-ams",
        "jti": secrets.token_hex(16),
    }
    return jwt.encode(
        payload,
        priv,
        algorithm=settings.JWT_ALGORITHM,
        headers={"kid": settings.JWT_KEY_ID},
    )


def mint_refresh_token(user, ip_address=None, user_agent=None) -> str:
    raw = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    RefreshToken.objects.create(
        user=user,
        token_hash=token_hash,
        expires_at=timezone.now() + timezone.timedelta(days=settings.REFRESH_TOKEN_EXPIRY_DAYS),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    return raw


def verify_refresh_token(raw: str):
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    row = RefreshToken.objects.select_related("user").filter(token_hash=token_hash).first()
    if not row or not row.is_valid:
        return None
    user = row.user
    if not user.is_active:
        return None
    return user, row


def verify_access_token(token: str):
    """Returns the claims dict, or None if the token is invalid/blacklisted."""
    _, pub = _load_keys()
    try:
        payload = jwt.decode(
            token,
            pub,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_exp": True, "verify_aud": False},
        )
    except jwt.PyJWTError:
        return None
    if payload.get("token_type") != "access":
        return None
    if payload.get("iss") != "fct-ams":
        return None
    if BlacklistedToken.objects.filter(jti=payload.get("jti")).exists():
        return None
    return payload


def blacklist_access_token(token: str):
    payload = verify_access_token(token)
    if payload and payload.get("jti"):
        BlacklistedToken.objects.create(
            jti=payload["jti"],
            user_id=payload.get("user_id"),
            expires_at=timezone.now() + timezone.timedelta(hours=settings.ACCESS_TOKEN_EXPIRY_HOURS),
        )


def get_user_id_from_access_token(token: str):
    payload = verify_access_token(token)
    return payload.get("user_id") if payload else None