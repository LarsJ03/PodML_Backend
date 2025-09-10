import boto3
from .config import settings

class AwsSessionFactory:
    """
    Lazy session factory. It does NOT create any service clients itself.
    Each service class asks for the session when it needs to initialize
    its own client.
    """
    _session = None

    @classmethod
    def get_session(cls) -> boto3.Session:
        if cls._session is None:
            cls._session = boto3.Session(region_name=settings.aws_region)
        print(cls._session)
        return cls._session
