"""
Model Context Protocol (MCP) Service - Dynamic B2B Multi-tenant client integration.

This service connects to external MCP servers registered by companies via SSE/HTTP,
discovers their tools dynamically, wraps them as LangChain StructuredTools, and
handles remote JSON-RPC execution. It includes memory caching (5-minute TTL)
to prevent latency on agent invocation.
"""
import asyncio
import logging
import threading
import time
from typing import List, Dict, Any, Optional

from langchain_core.tools import StructuredTool, BaseTool
from pydantic.v1 import BaseModel, Field, create_model

from mcp import ClientSession
from mcp.client.sse import sse_client
from models.mcp_config import CompanyMCPServer
from database import db_session

logger = logging.getLogger(__name__)


def run_async(coro):
    """
    Safely execute a coroutine synchronously, handling already running
    asyncio event loops in ASGI web environments.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running event loop, safe to run synchronously
        return asyncio.run(coro)

    # Event loop is running (FastAPI request thread). Run in a separate thread.
    result = None
    exception = None

    def target_thread():
        nonlocal result, exception
        try:
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            result = new_loop.run_until_complete(coro)
        except Exception as e:
            exception = e
        finally:
            new_loop.close()

    t = threading.Thread(target=target_thread)
    t.start()
    t.join()

    if exception:
        raise exception
    return result


class MCPService:
    """
    Handles connection lifecycle and tool translation for remote
    Model Context Protocol (MCP) servers.
    """

    # In-memory cache for dynamic tools (key: company_id -> value: (expiration_timestamp, list of tools))
    _tools_cache: Dict[int, tuple] = {}
    CACHE_TTL_SECONDS = 300  # 5 minutes cache TTL

    @classmethod
    def get_dynamic_tools_for_company(cls, company_id: int) -> List[BaseTool]:
        """
        Retrieves, translates, and wraps remote MCP server tools for a company.
        Implements in-memory caching to avoid round-trip handshakes on every message.
        """
        current_time = time.time()
        
        # Check cache validity
        if company_id in cls._tools_cache:
            exp_time, cached_tools = cls._tools_cache[company_id]
            if current_time < exp_time:
                logger.debug(f"[MCP] Returning {len(cached_tools)} cached tools for company {company_id}")
                return cached_tools

        # Cache miss, retrieve from remote MySQL database
        try:
            # Clean database session in case of stale connections
            try:
                db_session.rollback()
            except Exception:
                pass

            mcp_servers = db_session.query(CompanyMCPServer).filter_by(
                company_id=company_id, is_active=True
            ).all()

            if not mcp_servers:
                cls._tools_cache[company_id] = (current_time + cls.CACHE_TTL_SECONDS, [])
                return []

            logger.info(f"[MCP] Fetching tools from {len(mcp_servers)} active MCP servers for company {company_id}")
            
            dynamic_tools = []
            for server in mcp_servers:
                try:
                    server_tools = cls._fetch_tools_from_server(server)
                    dynamic_tools.extend(server_tools)
                except Exception as e:
                    logger.error(f"[MCP] Error loading tools from server '{server.name}' ({server.url}): {e}", exc_info=True)

            # Store in cache
            cls._tools_cache[company_id] = (current_time + cls.CACHE_TTL_SECONDS, dynamic_tools)
            return dynamic_tools

        except Exception as e:
            logger.error(f"[MCP] Error retrieving MCP servers for company {company_id}: {e}", exc_info=True)
            return []

    @classmethod
    def _fetch_tools_from_server(cls, server: CompanyMCPServer) -> List[BaseTool]:
        """
        Performs the remote SSE handshake and retrieves the list of tools.
        """
        async def _async_fetch():
            headers = server.headers or {}
            async with sse_client(url=server.url, headers=headers, timeout=3.0) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    result = await session.list_tools()
                    return result.tools

        try:
            mcp_tools = run_async(_async_fetch())
            logger.info(f"[MCP] Server '{server.name}' returned {len(mcp_tools)} tools.")
        except Exception as e:
            logger.warning(f"[MCP] Failed to connect to server '{server.name}': {e}")
            return []

        wrapped_tools = []
        for mcp_tool in mcp_tools:
            try:
                tool_instance = cls._wrap_mcp_tool(server, mcp_tool)
                wrapped_tools.append(tool_instance)
            except Exception as e:
                logger.error(f"[MCP] Error wrapping tool '{mcp_tool.name}' from '{server.name}': {e}", exc_info=True)

        return wrapped_tools

    @classmethod
    def _wrap_mcp_tool(cls, server: CompanyMCPServer, mcp_tool: Any) -> BaseTool:
        """
        Converts an MCP tool definition into a LangChain StructuredTool.
        Prefixes the name to avoid conflicts, e.g. "mcp_{server_slug}_{tool_name}".
        """
        # Prefix the name to prevent any collisions with native tools (e.g. "lookup_customer")
        safe_name = f"mcp_{server.name}_{mcp_tool.name}".lower().replace(" ", "_").replace("-", "_")
        
        # Build description with server context
        description = f"[MCP - {server.label}] {mcp_tool.description or 'No description provided'}"
        
        # Generate Pydantic V1 validation schema from JSON Schema
        input_schema = getattr(mcp_tool, 'inputSchema', None) or {}
        args_schema = cls._generate_pydantic_schema(safe_name, input_schema)
        
        # Define execution function wrapper
        def execute_wrapper(**kwargs):
            return cls._execute_remote_tool(
                server_url=server.url,
                headers=server.headers or {},
                mcp_tool_name=mcp_tool.name,
                arguments=kwargs
            )

        # Build the StructuredTool instance
        tool_instance = StructuredTool.from_function(
            func=execute_wrapper,
            name=safe_name,
            description=description,
            args_schema=args_schema,
            infer_schema=True
        )
        
        return tool_instance

    @classmethod
    def _generate_pydantic_schema(cls, tool_name: str, input_schema: dict) -> Optional[type]:
        """
        Converts a JSON Schema (from MCP) into a Pydantic V1 model.
        """
        properties = input_schema.get("properties", {})
        required = input_schema.get("required", [])
        
        if not properties:
            return None
            
        fields = {}
        for prop_name, prop_info in properties.items():
            prop_type = prop_info.get("type", "string")
            prop_desc = prop_info.get("description", "")
            
            # Map JSON Schema type to Python type
            if prop_type == "string":
                py_type = str
            elif prop_type == "integer":
                py_type = int
            elif prop_type == "number":
                py_type = float
            elif prop_type == "boolean":
                py_type = bool
            elif prop_type == "array":
                py_type = list
            elif prop_type == "object":
                py_type = dict
            else:
                py_type = str
                
            is_required = prop_name in required
            default_val = ... if is_required else None
            
            # Create Pydantic Field
            fields[prop_name] = (py_type, Field(default=default_val, description=prop_desc))
            
        try:
            model = create_model(f"{tool_name}_schema", **fields)
            return model
        except Exception as e:
            logger.error(f"[MCP] Failed to create dynamic args schema for '{tool_name}': {e}")
            return None

    @classmethod
    def _execute_remote_tool(
        cls, server_url: str, headers: dict, mcp_tool_name: str, arguments: dict
    ) -> str:
        """
        Synchronously invokes a remote MCP tool using the SSE client.
        Wraps remote call in strict timeouts and rollback cleanup.
        """
        async def _async_call():
            async with sse_client(url=server_url, headers=headers, timeout=5.0) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    result = await session.call_tool(mcp_tool_name, arguments)
                    
                    # Parse and format the result contents
                    if hasattr(result, 'content'):
                        text_parts = []
                        for item in result.content:
                            if hasattr(item, 'text'):
                                text_parts.append(item.text)
                            elif isinstance(item, dict) and "text" in item:
                                text_parts.append(item["text"])
                        return "\n".join(text_parts)
                    return str(result)

        try:
            logger.info(f"[MCP] Executing remote tool '{mcp_tool_name}' on '{server_url}'")
            response = run_async(_async_call())
            return response
        except Exception as e:
            logger.error(f"[MCP] Error calling remote tool '{mcp_tool_name}': {e}", exc_info=True)
            return f"Error executing tool '{mcp_tool_name}' remotely: {str(e)}"
