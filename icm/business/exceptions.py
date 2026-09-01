class BusinessError(Exception):
    """Business-layer error mapped to an HTTP response by the global exception handler."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)
