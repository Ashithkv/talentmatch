"""
Domain-specific exceptions.

Keeping these separate from FastAPI's HTTPException lets the service layer
stay framework-agnostic; routes translate these into the right HTTP status
codes and messages.
"""


class TalentMatchError(Exception):
    """Base class for all application-specific errors."""


class InvalidPDFError(TalentMatchError):
    """The uploaded file could not be parsed as a PDF."""


class EmptyResumeError(TalentMatchError):
    """The resume text is empty after extraction/validation."""


class MissingJobDescriptionError(TalentMatchError):
    """The job description text is empty."""


class MissingAPIKeyError(TalentMatchError):
    """No OpenAI API key is configured."""


class LLMFailureError(TalentMatchError):
    """The LLM call failed or returned something we couldn't use."""


class InvalidExtractedDataError(TalentMatchError):
    """The LLM returned data that failed schema validation."""
