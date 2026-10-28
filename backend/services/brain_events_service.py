"""
Brain Events Service
Emits real-time 'synaptic' brain events via Socket.IO to power the Living Brain Canvas.
Events are emitted to company rooms and picked up by the frontend visualization.

Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
"""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def _get_socketio():
    """Lazy import of socketio to avoid circular imports."""
    try:
        from extensions import socketio
        return socketio
    except Exception:
        return None


class BrainEventsService:
    """
    Emits agent 'synaptic' brain events via Socket.IO to the company room.
    All methods are non-blocking — errors are silently swallowed to never
    interrupt the AI agent processing pipeline.
    """

    @classmethod
    def _emit(cls, company_id: int, event: str, data: dict):
        """Core emit helper. Room = company_room_{company_id}."""
        try:
            sio = _get_socketio()
            if sio and company_id:
                room = f"company_room_{company_id}"
                payload = {**data, "ts": datetime.utcnow().isoformat(), "company_id": company_id}
                sio.emit(event, payload, room=room)
        except Exception as err:
            logger.warning(f"[BrainEvents] Failed to emit '{event}' for company {company_id}: {err}")

    @classmethod
    def emit_thought_start(cls, company_id: int, agent_name: str, query_preview: str = ""):
        """
        Emitted when the LangGraph agent begins processing a message.
        Lights up the Conductor / Query node.
        """
        cls._emit(company_id, "AGENT_THOUGHT_START", {
            "event": "AGENT_THOUGHT_START",
            "agent_name": agent_name,
            "query_preview": query_preview[:120] if query_preview else "",
            "node_type": "conductor",
        })

    @classmethod
    def emit_rag_query(cls, company_id: int, query: str, agent_id: int = None):
        """
        Emitted when a Pinecone / vector search begins.
        Pulses the Memory Core → RAG cluster nodes.
        """
        cls._emit(company_id, "RAG_QUERY_START", {
            "event": "RAG_QUERY_START",
            "query": query[:120] if query else "",
            "agent_id": agent_id,
            "node_type": "rag_query",
        })

    @classmethod
    def emit_rag_hit(cls, company_id: int, doc_id: str, filename: str,
                     relevance_score: float = 0.0, chunk_preview: str = ""):
        """
        Emitted when a document chunk is retrieved from the vector store.
        Lights up the specific RAG chunk node.
        """
        cls._emit(company_id, "RAG_HIT", {
            "event": "RAG_HIT",
            "doc_id": str(doc_id),
            "filename": filename,
            "relevance_score": round(float(relevance_score), 4),
            "chunk_preview": chunk_preview[:150] if chunk_preview else "",
            "node_type": "rag_chunk",
        })

    @classmethod
    def emit_tool_dispatch(cls, company_id: int, tool_name: str, agent_id: int = None,
                           input_preview: str = ""):
        """
        Emitted when a LangChain tool is invoked (WhatsApp send, Stripe, Pinecone, etc.).
        Sends a photon spark from Agent → Tool node.
        """
        cls._emit(company_id, "TOOL_DISPATCH", {
            "event": "TOOL_DISPATCH",
            "tool_name": tool_name,
            "agent_id": agent_id,
            "input_preview": input_preview[:100] if input_preview else "",
            "node_type": "tool",
        })

    @classmethod
    def emit_tool_result(cls, company_id: int, tool_name: str,
                         status: str = "success", result_preview: str = ""):
        """
        Emitted when a tool returns its result.
        Changes the tool node color: green=success, red=error.
        """
        cls._emit(company_id, "TOOL_RESULT", {
            "event": "TOOL_RESULT",
            "tool_name": tool_name,
            "status": status,
            "result_preview": result_preview[:100] if result_preview else "",
            "node_type": "tool",
        })

    @classmethod
    def emit_response_complete(cls, company_id: int, agent_name: str,
                               tokens_used: int = 0, channel: str = "whatsapp"):
        """
        Emitted when the final AI response is assembled and ready to send.
        Triggers the completion ripple wave across the graph.
        """
        cls._emit(company_id, "AGENT_RESPONSE_COMPLETE", {
            "event": "AGENT_RESPONSE_COMPLETE",
            "agent_name": agent_name,
            "tokens_used": tokens_used,
            "channel": channel,
            "node_type": "conductor",
        })

    @classmethod
    def emit_synapse_pulse(cls, company_id: int, active_agents: int = 0):
        """
        General heartbeat / idle pulse for the brain canvas when there are active agents.
        """
        cls._emit(company_id, "SYNAPSE_PULSE", {
            "event": "SYNAPSE_PULSE",
            "active_agents": active_agents,
            "node_type": "pulse",
        })
