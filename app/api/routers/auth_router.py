from fastapi import APIRouter, HTTPException
from ...schemas.auth import CheckEmailIn, CheckEmailOut
from ...services.cognito_service import CognitoService
from ...core.exceptions import ServiceError

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/check-email", response_model=CheckEmailOut)
def check_email(payload: CheckEmailIn):
    """
    POST /auth/check-email
    Body: { "email": "user@example.com" }
    Returns: { "exists": true|false }
    """
    svc = CognitoService()
    try:
        exists = svc.email_exists(payload.email)
        return CheckEmailOut(exists=exists)
    except ServiceError as e:
        # Hide provider specifics from the client
        raise HTTPException(status_code=500, detail=str(e))
