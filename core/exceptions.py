# structured exception handling

class InfraAuditError(Exception):
    """Base exception for all InfraAudit errors."""
    pass

class APIConnectionError(InfraAuditError):
    """Raised when an external API cannot be reached after retries."""
    pass