"""Module for custom exceptions"""

class YandException(Exception):
    """Generic exception"""

class StatusProgramError(YandException):
    """Raised when programming of the NAND Flash failed"""
