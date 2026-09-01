from rest_framework import status


class ServiceError(Exception):
    def __init__(self, message, status_code=status.HTTP_400_BAD_REQUEST, code="service_error"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
