from contextvars import ContextVar
from services.service import MCQService

# Context variable to hold the MCQService instance for the current user session
_mcq_service_ctx = ContextVar("mcq_service", default=None)

def get_service() -> MCQService:
    """
    Retrieves the MCQService instance for the current context.
    If no service is set (e.g., during testing or script execution without context),
    it returns a default instance to prevent crashes, though state isolation won't apply.
    """
    service = _mcq_service_ctx.get()
    if service is None:
        # Fallback for non-context execution (scripts, tests)
        # Note: This creates a new service each time if not set, 
        # which might not be desired for state persistence in scripts unless handled there.
        # For the web app, this should always be set.
        return MCQService() 
    return service

def set_service(service: MCQService):
    """Sets the MCQService instance for the current context."""
    _mcq_service_ctx.set(service)

