"""
Company MCP Config API Routes - CRUD operations for Model Context Protocol servers.

Endpoints:
    GET    /api/companies/<id>/mcp         - List all registered MCP servers
    POST   /api/companies/<id>/mcp         - Register a new MCP server
    PUT    /api/companies/<id>/mcp/<sid>   - Update MCP server config
    DELETE /api/companies/<id>/mcp/<sid>   - Delete an MCP server config
    POST   /api/companies/<id>/mcp/<sid>/toggle - Toggle active/inactive status
    POST   /api/companies/<id>/mcp/<sid>/test   - Test connection and fetch remote tools
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from database import get_db
from sqlalchemy.orm import Session

from models.mcp_config import CompanyMCPServer
from services.mcp_service import MCPService

router = APIRouter(prefix="/api/companies/{company_id}/mcp", tags=["mcp"])


# ── Pydantic Schemas ──────────────────────────────────────────────────────

class MCPServerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    label: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    url: str = Field(..., min_length=1, max_length=512)
    headers: Optional[Dict[str, Any]] = {}
    is_active: Optional[bool] = True


class MCPServerUpdate(BaseModel):
    label: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    headers: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


# ── Endpoints ─────────────────────────────────────────────────────────────

@router.get("")
def list_mcp_servers(company_id: int, db: Session = Depends(get_db)):
    """List all registered MCP servers for a company."""
    servers = (
        CompanyMCPServer.query
        .filter_by(company_id=company_id)
        .order_by(CompanyMCPServer.created_at.desc())
        .all()
    )
    return {"servers": [s.to_dict() for s in servers]}


@router.post("")
def register_mcp_server(company_id: int, data: MCPServerCreate, db: Session = Depends(get_db)):
    """Register a new remote MCP server for a company."""
    # Check for duplicate slug name
    slug_name = data.name.strip().lower().replace(" ", "-")
    existing = CompanyMCPServer.query.filter_by(
        company_id=company_id, name=slug_name
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"MCP Server '{slug_name}' is already registered for this company."
        )

    server = CompanyMCPServer(
        company_id=company_id,
        name=slug_name,
        label=data.label,
        description=data.description,
        url=data.url.strip(),
        headers=data.headers or {},
        is_active=data.is_active if data.is_active is not None else True,
    )
    db.add(server)
    db.commit()
    db.refresh(server)

    # Invalidate cache so tools reload on next request
    if company_id in MCPService._tools_cache:
        del MCPService._tools_cache[company_id]

    return {"server": server.to_dict(), "message": "MCP Server registered successfully."}


@router.put("/{server_id}")
def update_mcp_server(
    company_id: int, server_id: int, data: MCPServerUpdate, db: Session = Depends(get_db)
):
    """Update an MCP server's connection settings."""
    server = CompanyMCPServer.query.filter_by(
        id=server_id, company_id=company_id
    ).first()
    if not server:
        raise HTTPException(status_code=404, detail="MCP Server not found.")

    if data.label is not None:
        server.label = data.label
    if data.description is not None:
        server.description = data.description
    if data.url is not None:
        server.url = data.url.strip()
    if data.headers is not None:
        server.headers = data.headers
    if data.is_active is not None:
        server.is_active = data.is_active

    db.commit()
    db.refresh(server)

    # Invalidate cache so tools reload on next request
    if company_id in MCPService._tools_cache:
        del MCPService._tools_cache[company_id]

    return {"server": server.to_dict(), "message": "MCP Server config updated successfully."}


@router.delete("/{server_id}")
def delete_mcp_server(company_id: int, server_id: int, db: Session = Depends(get_db)):
    """Delete an MCP server registration."""
    server = CompanyMCPServer.query.filter_by(
        id=server_id, company_id=company_id
    ).first()
    if not server:
        raise HTTPException(status_code=404, detail="MCP Server not found.")

    db.delete(server)
    db.commit()

    # Invalidate cache so tools reload on next request
    if company_id in MCPService._tools_cache:
        del MCPService._tools_cache[company_id]

    return {"message": f"MCP Server '{server.name}' deleted successfully."}


@router.post("/{server_id}/toggle")
def toggle_mcp_server(company_id: int, server_id: int, db: Session = Depends(get_db)):
    """Toggle a server's active/inactive status."""
    server = CompanyMCPServer.query.filter_by(
        id=server_id, company_id=company_id
    ).first()
    if not server:
        raise HTTPException(status_code=404, detail="MCP Server not found.")

    server.is_active = not server.is_active
    db.commit()
    db.refresh(server)

    # Invalidate cache
    if company_id in MCPService._tools_cache:
        del MCPService._tools_cache[company_id]

    state = "activated" if server.is_active else "deactivated"
    return {
        "server": server.to_dict(),
        "message": f"MCP Server '{server.name}' has been {state}."
    }


@router.post("/{server_id}/test")
def test_mcp_server_connection(company_id: int, server_id: int, db: Session = Depends(get_db)):
    """
    Test connection to a remote MCP server and fetch list of tools.
    Acts as a validation endpoint for dashboard testing.
    """
    server = CompanyMCPServer.query.filter_by(
        id=server_id, company_id=company_id
    ).first()
    if not server:
        raise HTTPException(status_code=404, detail="MCP Server not found.")

    try:
        wrapped_tools = MCPService._fetch_tools_from_server(server)
        if not wrapped_tools:
            return {
                "status": "warning",
                "message": "Connected to server, but it returned no tools.",
                "tools": []
            }
            
        tool_schemas = []
        for t in wrapped_tools:
            # Safely serialize schema for UI
            tool_schemas.append({
                "name": t.name,
                "description": t.description,
                "arguments": getattr(t.args_schema, '__fields__', {}) if t.args_schema else {}
            })
            
        return {
            "status": "success",
            "message": f"Successfully connected! Discovered {len(wrapped_tools)} tools.",
            "tools": tool_schemas
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Connection failed: {str(e)}",
            "tools": []
        }
