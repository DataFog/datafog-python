"""
Exceptions module for DataFog SDK.

This module defines custom exceptions and utility functions for error handling in the DataFog SDK.
"""

from typing import Optional


class DataFogException(Exception):
    """
    Base exception for DataFog SDK.

    Attributes:
        message (str): The error message.
        status_code (int, optional): The HTTP status code associated with the error.
    """

    def __init__(self, message: str, status_code: Optional[int] = None):
        """
        Initialize a DataFogException.

        Args:
            message (str): The error message.
            status_code (int, optional): The HTTP status code associated with the error.
        """
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class BadRequestError(DataFogException):
    """
    Exception raised for 400 Bad Request errors.

    Inherits from DataFogException and sets the status code to 400.
    """

    def __init__(self, message: str):
        """
        Initialize a BadRequestError.

        Args:
            message (str): The error message.
        """
        super().__init__(message, status_code=400)


class UnprocessableEntityError(DataFogException):
    """
    Exception raised for 422 Unprocessable Entity errors.

    Inherits from DataFogException and sets the status code to 422.
    """

    def __init__(self, message: str):
        """
        Initialize an UnprocessableEntityError.

        Args:
            message (str): The error message.
        """
        super().__init__(message, status_code=422)


def raise_for_status_code(status_code: int, error_message: str):
    """
    Raise the appropriate exception based on the status code.

    Args:
        status_code (int): The HTTP status code.
        error_message (str): The error message to include in the exception.

    Raises:
        BadRequestError: If the status code is 400.
        UnprocessableEntityError: If the status code is 422.
    """
    if status_code == 400:
        raise BadRequestError(error_message)
    elif status_code == 422:
        raise UnprocessableEntityError(error_message)
