import os
import sys
import time
import asyncio
import threading
import uuid
import json
from typing import Dict, Any

# Ensure backend folder is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import db_session
from models.company import Company
from models.mcp_config import CompanyMCPServer
from services.mcp_service import MCPService

# Mock Server setup using FastAPI and uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import uvicorn

app = FastAPI()
queues = {}

@app.get("/sse")
async def sse_endpoint(request: Request):
    session_id = str(uuid.uuid4())
    queue = asyncio.Queue()
    queues[session_id] = queue
    
    async def event_generator():
        # First send the endpoint event to tell the client where to POST messages
        yield f"event: endpoint\ndata: /messages?session_id={session_id}\n\n"
        
        try:
            while True:
                message = await queue.get()
                yield f"data: {json.dumps(message)}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            if session_id in queues:
                del queues[session_id]

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/messages")
async def messages_endpoint(request: Request, session_id: str):
    payload = await request.json()
    msg_id = payload.get("id")
    method = payload.get("method")
    
    # Notifications do not have an id and should not receive a response
    if msg_id is None:
        return {"status": "accepted"}
    
    response = {
        "jsonrpc": "2.0",
        "id": msg_id
    }
    
    if method == "initialize":
        response["result"] = {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "mock-server",
                "version": "1.0.0"
            }
        }
    elif method == "tools/list":
        response["result"] = {
            "tools": [
                {
                    "name": "calculate_tax",
                    "description": "Calculate dynamic tax for an order amount.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "amount": {
                                "type": "number",
                                "description": "The order amount in USD."
                            },
                            "state": {
                                "type": "string",
                                "description": "Two-letter US state code."
                            }
                        },
                        "required": ["amount", "state"]
                    }
                }
            ]
        }
    elif method == "tools/call":
        params = payload.get("params", {})
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name == "calculate_tax":
            amount = arguments.get("amount", 0.0)
            state = arguments.get("state", "CA").upper()
            tax = amount * 0.08 if state == "CA" else amount * 0.05
            response["result"] = {
                "content": [
                    {
                        "type": "text",
                        "text": f"Tax for {amount} in {state} is {tax:.2f} (Total: {amount + tax:.2f})"
                    }
                ]
            }
        else:
            response["error"] = {
                "code": -32601,
                "message": f"Method not found: {tool_name}"
            }
    else:
        response["error"] = {
            "code": -32601,
            "message": f"Method not found: {method}"
        }
        
    if session_id in queues:
        await queues[session_id].put(response)
        return {"status": "accepted"}
    else:
        return {"status": "error", "message": "Session not found"}

def run_mock_server():
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="warning")

def main():
    print("Starting mock MCP Server thread on http://127.0.0.1:8001/sse...")
    server_thread = threading.Thread(target=run_mock_server, daemon=True)
    server_thread.start()
    
    # Wait for server to start
    time.sleep(2)
    
    company = None
    server_record = None
    try:
        # Find a company
        company = db_session.query(Company).first()
        if not company:
            print("❌ Error: No company found in database to run tests against.")
            return
            
        print(f"Testing with Company ID: {company.id} ({company.name})")
        
        # Clean any preexisting mock config
        existing = db_session.query(CompanyMCPServer).filter_by(
            company_id=company.id, name="mock-server"
        ).first()
        if existing:
            db_session.delete(existing)
            db_session.commit()
            
        # Register the mock MCP server
        server_record = CompanyMCPServer(
            company_id=company.id,
            name="mock-server",
            label="Mock Server",
            description="Testing Model Context Protocol client implementation",
            url="http://127.0.0.1:8001/sse",
            headers={},
            is_active=True
        )
        db_session.add(server_record)
        db_session.commit()
        db_session.refresh(server_record)
        print(f"Created CompanyMCPServer record with ID: {server_record.id}")
        
        # Invalidate any cached tools for this company
        if company.id in MCPService._tools_cache:
            del MCPService._tools_cache[company.id]
            
        # Test tool retrieval
        print("\n--- Retrieving dynamic tools for company ---")
        tools = MCPService.get_dynamic_tools_for_company(company.id)
        print(f"Found {len(tools)} tools:")
        for t in tools:
            print(f" - Tool Name: {t.name}")
            print(f"   Description: {t.description}")
            print(f"   Schema: {t.args_schema}")
            
        # Verify calculation tool exists
        tax_tool = next((t for t in tools if "calculate_tax" in t.name), None)
        if not tax_tool:
            print("❌ Error: calculate_tax tool not found in list of tools.")
            return
            
        print("\n--- Executing remote tool ---")
        result = tax_tool.invoke({"amount": 150.0, "state": "CA"})
        print(f"Result from remote tool: {result}")
        
        if "Tax for 150.0 in CA is 12.00" in result:
            print("\n✅ MCP INTEGRATION SUCCESSFUL!")
        else:
            print("\n❌ MCP INTEGRATION FAILED: Unexpected response.")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Clean up database record
        if server_record:
            try:
                db_session.delete(server_record)
                db_session.commit()
                print("Cleaned up CompanyMCPServer database record.")
            except Exception as e:
                print(f"Failed to clean up db record: {e}")
        db_session.remove()

if __name__ == "__main__":
    main()
