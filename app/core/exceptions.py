class ServiceError(Exception):
    """Generic service-layer error to avoid leaking provider details."""
    def __init__(self, message: str, *, cause: Exception | None = None):
        super().__init__(message)
        self.cause = cause
