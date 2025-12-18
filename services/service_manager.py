from contextvars import ContextVar
from services.service import MCQService, OpenEndedService, UnifiedPerformanceService

# Context variable to hold the MCQService instance for the current user session
_mcq_service_ctx = ContextVar("mcq_service", default=None)
_open_service_ctx = ContextVar("open_service", default=None)
_unified_performance_ctx = ContextVar("unified_performance", default=None)

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

def get_open_service() -> OpenEndedService:
    """Returns OpenEndedService for current context, or creates default if unset."""
    service = _open_service_ctx.get()
    if service is None:
        return OpenEndedService()
    return service

def set_open_service(service: OpenEndedService):
    """Sets OpenEndedService for current context."""
    _open_service_ctx.set(service)

def get_unified_performance() -> UnifiedPerformanceService:
    """Returns UnifiedPerformanceService for current context, or creates with current services."""
    service = _unified_performance_ctx.get()
    if service is None:
        mcq_svc = get_service()
        open_svc = get_open_service()
        return UnifiedPerformanceService(mcq_svc, open_svc)
    return service

def set_unified_performance(service: UnifiedPerformanceService):
    """Sets UnifiedPerformanceService for current context."""
    _unified_performance_ctx.set(service)

def initialize_session_services():
    """Initializes all services for a new session. Call at session start."""
    mcq_svc = MCQService()
    open_svc = OpenEndedService()
    unified_svc = UnifiedPerformanceService(mcq_svc, open_svc)

    set_service(mcq_svc)
    set_open_service(open_svc)
    set_unified_performance(unified_svc)
