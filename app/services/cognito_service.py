from typing import Optional, Dict, Any
from botocore.client import BaseClient
from ..core.aws import AwsSessionFactory
from ..core.config import settings
from ..core.exceptions import ServiceError

class CognitoService:
    """
    Cognito-specific operations encapsulated in a class.
    Client is initialized lazily in __init__, so no global clients or
    cross-service eager initialization happens.
    """

    def __init__(self, *, user_pool_id: Optional[str] = None):
        # create client only for this service
        session = AwsSessionFactory.get_session()
        self.client: BaseClient = session.client("cognito-idp")
        self.user_pool_id = user_pool_id or settings.aws_cognito_user_pool_id


    def email_exists(self, email: str) -> bool:
        """
        Server-side existence check using ListUsers with email filter.
        Works even if username != email.
        """

        resp = self.client.list_users(
            UserPoolId=self.user_pool_id,
            Filter=f'email = "{email}"',
            Limit=1,
        )
        return bool(resp.get("Users"))


    def get_user_by_sub(self, sub: str) -> Optional[Dict[str, Any]]:
        """
        Example helper (if you ever set username==sub you can admin_get_user).
        """
        try:
            try:
                out = self.client.admin_get_user(
                    UserPoolId=self.user_pool_id,
                    Username=sub,
                )
                return out
            except self.client.exceptions.UserNotFoundException:
                return None
        except Exception as err:
            raise ServiceError("Failed to fetch user by sub from Cognito", cause=err)
