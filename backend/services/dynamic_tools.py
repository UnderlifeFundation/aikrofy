"""
Dynamic Tools Service - Enterprise 10X
Translates no-code DynamicAction definitions into LangChain BaseTool instances.
Supports runtime validation, custom headers, Pydantic dynamic models,
and seamless registration with LangGraphAgentService.
"""
import logging
import httpx
from typing import List, Dict, Any, Optional
from langchain_core.tools import StructuredTool, BaseTool
from pydantic import create_model, Field
from models.dynamic_action import DynamicAction, HttpMethod, AuthType
from models.company import Company

logger = logging.getLogger(__name__)

class DynamicToolsService:
    """Compiles DynamicAction DB records into executable LangChain tools"""

    @classmethod
    def get_tools_for_company(cls, company_id: int) -> List[BaseTool]:
        """Loads all active dynamic actions for a company and generates LangChain tools"""
        try:
            actions = DynamicAction.query.filter_by(company_id=company_id, is_active=True).all()
            tools = []
            for action in actions:
                tool = cls._build_tool_from_action(action)
                if tool:
                    tools.append(tool)
            return tools
        except Exception as e:
            logger.error(f"[DYNAMIC TOOLS] Error loading actions for company {company_id}: {e}")
            return []

    @classmethod
    def _build_tool_from_action(cls, action: DynamicAction) -> Optional[BaseTool]:
        """Builds a single StructuredTool instance from a DynamicAction record"""
        try:
            fields = {}
            for param in (action.parameters_schema or []):
                p_name = param.get('name')
                p_type = str if param.get('type') == 'string' else (int if param.get('type') == 'integer' else (float if param.get('type') == 'number' else (bool if param.get('type') == 'boolean' else Any)))
                p_desc = param.get('description', '')
                p_req = param.get('required', True)
                if p_req:
                    fields[p_name] = (p_type, Field(..., description=p_desc))
                else:
                    fields[p_name] = (Optional[p_type], Field(None, description=p_desc))

            # Dynamic Pydantic schema model
            args_schema = create_model(f"{action.name}_args", **fields) if fields else None

            # Execution wrapper function
            def execute_action(**kwargs) -> str:
                return cls._execute_http_action(action, kwargs)

            execute_action.__doc__ = action.description or f"Custom action: {action.display_name}"
            execute_action.__name__ = action.name

            return StructuredTool.from_function(
                func=execute_action,
                name=action.name,
                description=action.description or action.display_name,
                args_schema=args_schema
            )
        except Exception as err:
            logger.error(f"[DYNAMIC TOOLS] Failed to build tool {action.name}: {err}")
            return None

    @classmethod
    def _execute_http_action(cls, action: DynamicAction, params: Dict[str, Any]) -> str:
        """Performs the actual outbound HTTP request with auth and parameters"""
        method = action.http_method.value if hasattr(action.http_method, 'value') else str(action.http_method)
        url = action.endpoint_url
        headers = dict(action.headers or {})
        
        # Authentication injection
        auth_type = action.auth_type.value if hasattr(action.auth_type, 'value') else str(action.auth_type)
        auth_config = action.auth_config or {}

        if auth_type == AuthType.BEARER.value:
            token = auth_config.get('token') or auth_config.get('api_key')
            if token:
                headers['Authorization'] = f"Bearer {token}"
        elif auth_type == AuthType.API_KEY.value:
            header_key = auth_config.get('header_key', 'X-API-KEY')
            token = auth_config.get('api_key') or auth_config.get('token')
            if token:
                headers[header_key] = token
        elif auth_type == AuthType.CUSTOM_HEADER.value:
            for k, v in (auth_config.get('custom_headers') or {}).items():
                headers[k] = v

        try:
            with httpx.Client(timeout=15.0) as client:
                if method.upper() == 'GET':
                    response = client.get(url, params=params, headers=headers)
                elif method.upper() == 'POST':
                    payload = dict(action.static_payload or {})
                    payload.update(params)
                    response = client.post(url, json=payload, headers=headers)
                elif method.upper() == 'PUT':
                    payload = dict(action.static_payload or {})
                    payload.update(params)
                    response = client.put(url, json=payload, headers=headers)
                elif method.upper() == 'PATCH':
                    payload = dict(action.static_payload or {})
                    payload.update(params)
                    response = client.patch(url, json=payload, headers=headers)
                elif method.upper() == 'DELETE':
                    response = client.delete(url, params=params, headers=headers)
                else:
                    return f"Error: Unsupported HTTP method {method}"

                if response.status_code >= 400:
                    return f"Action API error (HTTP {response.status_code}): {response.text[:300]}"

                try:
                    res_json = response.json()
                    # Optional key filter
                    if action.response_path and isinstance(res_json, dict):
                        return str(res_json.get(action.response_path, res_json))
                    return str(res_json)
                except Exception:
                    return response.text[:500]

        except Exception as req_err:
            logger.error(f"[DYNAMIC TOOLS] HTTP execution failed for {action.name}: {req_err}")
            return f"Failed to execute external action {action.name}: {str(req_err)}"
