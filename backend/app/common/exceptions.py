class VideoGenException(Exception):
    """Base exception for video generation"""
    pass

class PhaseException(VideoGenException):
    """Exception during phase execution"""
    pass

class ExternalAPIException(VideoGenException):
    """Exception from external API"""
    pass

class ValidationException(VideoGenException):
    """Validation error"""
    pass
