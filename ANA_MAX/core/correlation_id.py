import contextvars
import logging
import uuid

# Context variable that holds the correlation ID for the current request/thread
_correlation_id = contextvars.ContextVar('correlation_id', default=None)

def set_correlation_id(cid: str = None) -> str:
    """Set the correlation ID for the current context.

    If *cid* is ``None`` a new UUID4 string is generated.
    The ID is stored in the ``ContextVar`` so it propagates through async
    calls and threads that share the same context.
    """
    if not cid:
        cid = str(uuid.uuid4())
    _correlation_id.set(cid)
    return cid

def get_correlation_id() -> str:
    """Retrieve the correlation ID from the current context.

    Returns ``None`` if no ID has been set.
    """
    return _correlation_id.get()

class CorrelationIdFilter(logging.Filter):
    """Inject ``correlation_id`` into every ``LogRecord``.

    The ``logging`` module will raise ``ValueError`` when a formatter
    references ``%(correlation_id)s`` and the attribute is missing. This
    filter guarantees the attribute is always present – an empty string if
    no ID has been configured.
    """
    def filter(self, record: logging.LogRecord) -> bool:
        cid = get_correlation_id()
        record.correlation_id = cid if cid else ""
        return True
