"""
Turn Telemetry — real, per-turn observability data for the Observatory.

Why this exists
---------------
Assistant messages are created in ~11 different places (chat, webhooks, voice, ...).
Instead of editing each one, the agent services record what actually happened during a
turn (LEM energy, token usage, model, credits, latency) into a ContextVar, and a
SQLAlchemy ``before_insert`` listener attaches it to the assistant ``Message`` row that
is persisted right after — in the same thread/context.

Nothing here is simulated: if a value was not measured it is simply absent and the UI
renders "—" rather than inventing a number.
"""
from __future__ import annotations

import logging
import time
from contextvars import ContextVar
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# A turn's telemetry is only attachable for this long; protects against a stale record
# leaking onto an unrelated message if a code path forgot to persist its reply.
_MAX_AGE_SECONDS = 300

_current: ContextVar[Optional[Dict[str, Any]]] = ContextVar('turn_telemetry', default=None)
_registered = False


def begin() -> None:
    """Start measuring a turn. Call at the very top of ``process_message``."""
    register()
    _current.set({'_t0': time.monotonic(), 'spans': []})


def record(**fields: Any) -> None:
    """Merge measured values into the active turn (no-op if no turn is active)."""
    cur = _current.get()
    if cur is None:
        return
    for key, value in fields.items():
        if value is not None:
            cur[key] = value


def add_span(name: str, kind: str, status: str = 'ok', **extra: Any) -> None:
    """Append a measured step (guardrail, rag, llm, tool...) to the turn."""
    cur = _current.get()
    if cur is None:
        return
    span = {
        'name': name,
        'kind': kind,
        'status': status,
        'at_ms': int((time.monotonic() - cur['_t0']) * 1000),
    }
    span.update({k: v for k, v in extra.items() if v is not None})
    cur['spans'].append(span)


def consume() -> Optional[Dict[str, Any]]:
    """Return and clear the active turn's telemetry, finalising latency."""
    cur = _current.get()
    if not cur:
        return None
    _current.set(None)
    age = time.monotonic() - cur['_t0']
    if age > _MAX_AGE_SECONDS:
        return None
    out = {k: v for k, v in cur.items() if not k.startswith('_')}
    out['latency_ms'] = int(age * 1000)
    return out


def register() -> None:
    """Attach the Message listener once. Imported lazily to avoid circular imports."""
    global _registered
    if _registered:
        return
    try:
        from sqlalchemy import event
        from models.conversation import Message, MessageRole

        @event.listens_for(Message, 'before_insert')
        def _attach(mapper, connection, target):  # noqa: ANN001
            try:
                role = target.role.value if hasattr(target.role, 'value') else str(target.role)
                if str(role).lower() != MessageRole.ASSISTANT.value:
                    return
                data = consume()
                if not data:
                    return
                if target.tokens_used is None:
                    usage = data.get('usage') or {}
                    total = usage.get('total_tokens')
                    if total is not None:
                        target.tokens_used = int(total)
                if target.latency_ms is None:
                    target.latency_ms = data.get('latency_ms')
                target.trace_meta = data
            except Exception as exc:  # telemetry must never break message persistence
                logger.warning('[TURN_TELEMETRY] attach failed: %s', exc)

        _registered = True
    except Exception as exc:
        logger.warning('[TURN_TELEMETRY] listener registration failed: %s', exc)
