# backend/app/services/cognito_jwt_verifier.py
import time
from typing import Any, Dict, Optional

import httpx
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError, JWKError, JWTError

from ..core.config import settings


def _issuer() -> str:
    # e.g. https://cognito-idp.eu-central-1.amazonaws.com/eu-central-1_ABC123
    return f"https://cognito-idp.{settings.aws_region}.amazonaws.com/{settings.aws_cognito_user_pool_id}"


def _jwks_url() -> str:
    return f"{_issuer()}/.well-known/jwks.json"


class CognitoJWTVerifier:
    """Verifies Cognito ID tokens against JWKS (no boto3)."""
    _jwks_cache: Optional[Dict[str, Any]] = None
    _jwks_fetched_at: float = 0.0
    _jwks_ttl_seconds: int = 3600

    @classmethod
    def _get_jwks(cls) -> Dict[str, Any]:
        now = time.time()
        if cls._jwks_cache and (now - cls._jwks_fetched_at) < cls._jwks_ttl_seconds:
            return cls._jwks_cache
        resp = httpx.get(_jwks_url(), timeout=10.0)
        resp.raise_for_status()
        cls._jwks_cache = resp.json()
        cls._jwks_fetched_at = now
        return cls._jwks_cache

    @classmethod
    def verify_id_token(cls, token: str) -> Dict[str, Any]:
        # 1) header + matching JWK
        try:
            hdr = jwt.get_unverified_header(token)
        except Exception as e:
            raise ValueError("Malformed token header") from e

        kid = hdr.get("kid")
        if not kid:
            raise ValueError("Missing 'kid' in token header")

        jwk = next((k for k in cls._get_jwks().get("keys", []) if k.get("kid") == kid), None)
        if not jwk:
            raise ValueError("Signing key not found in JWKS (kid mismatch)")

        # 2) verify signature & claims (NO 'leeway' kwarg)
        try:
            claims = jwt.decode(
                token,
                jwk,  # python-jose accepts JWK dict
                algorithms=[jwk.get("alg", "RS256")],
                audience=settings.aws_cognito_client_id,  # must equal token 'aud'
                issuer=_issuer(),                         # must equal token 'iss'
                options={"verify_at_hash": False},
            )
        except ExpiredSignatureError as e:
            raise ValueError("Token expired") from e
        except JWTClaimsError as e:
            raise ValueError(f"JWT claims invalid: {e}") from e
        except (JWKError, JWTError) as e:
            raise ValueError(f"JWT signature/format invalid: {e}") from e

        # 3) Manual clock skew tolerance (60s)
        try:
            exp = int(claims.get("exp", 0))
            now = int(time.time())
            if now > exp + 60:
                raise ValueError("Token expired (after skew)")
        except (TypeError, ValueError):
            raise ValueError("Token missing or invalid 'exp' claim")

        # 4) ensure it's an ID token
        tu = claims.get("token_use")
        if tu != "id":
            raise ValueError(f"Wrong token_use='{tu}', expected 'id'")

        return claims

    @classmethod
    def sub_from_token(cls, token: str) -> str:
        return str(cls.verify_id_token(token)["sub"])
