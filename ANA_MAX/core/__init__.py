"""
A.N.A. v15.0 - Core Package
===========================
Agent AI cu auto-evolutie si protectie privacy.
"""

from .event_stream import BusEvent, EventBus, EventLog, EventStream, EventType, get_event_stream

__version__ = "15.0.0"
__author__ = "A.N.A. Development Team"

__all__ = [
    "BusEvent",
    "EventBus",
    "EventLog",
    "EventStream",
    "EventType",
    "get_event_stream",
]
