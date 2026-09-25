"""Publishes the RS256 public key so downstream factory modules can verify AMS JWTs."""

from django.http import JsonResponse

from .jwt_utils import get_public_key_pem


def jwks_view(request):
    from cryptography.hazmat.primitives import serialization

    from django.conf import settings

    pub = get_public_key_pem()
    public_key = serialization.load_pem_public_key(pub)
    numbers = public_key.public_numbers()
    n = numbers.n.to_bytes((numbers.n.bit_length() + 7) // 8, "big")
    e = numbers.e.to_bytes((numbers.e.bit_length() + 7) // 8, "big")

    def _b64u(raw):
        import base64

        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")

    return JsonResponse(
        {
            "keys": [
                {
                    "kty": "RSA",
                    "use": "sig",
                    "alg": settings.JWT_ALGORITHM,
                    "kid": settings.JWT_KEY_ID,
                    "n": _b64u(n),
                    "e": _b64u(e),
                }
            ]
        }
    )