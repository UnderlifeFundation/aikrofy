"""
Voice Agent Tools
Defines tools that can be used by the Voice Agent.
These tools act as bridges to the main PymAI API via internal endpoints.
"""
import os
import logging
import json
import aiohttp
from livekit.agents import function_tool, RunContext, get_job_context
from typing import Optional

# Internal API URL (configurable for production)
API_URL = os.getenv("PYMAI_API_URL", "http://localhost:5010")

async def execute_remote_tool(tool_name: str, arguments: dict) -> str:
    """Helper to call internal API to execute tool"""
    try:
        # Get context from room metadata
        ctx = get_job_context()
        metadata = json.loads(ctx.room.metadata or "{}")
        company_id = metadata.get("company_id")
        agent_id = metadata.get("agent_id")
        
        if not company_id:
            return "Error: context missing company_id"

        payload = {
            "company_id": company_id,
            "agent_id": agent_id,
            "tool_name": tool_name,
            "arguments": arguments
        }
        
        # Include internal API token for authentication
        headers = {'Content-Type': 'application/json'}
        internal_token = os.getenv('INTERNAL_API_TOKEN')
        if internal_token:
            headers['X-Internal-Token'] = internal_token
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{API_URL}/api/internal/execute-tool", json=payload, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    # Parse result for friendly voice output
                    if result.get('success'):
                        return result.get('message', "Action completed successfully.")
                    else:
                        return f"Error: {result.get('error', 'Unknown error')}"
                else:
                    text = await response.text()
                    logging.error(f"API Error ({response.status}): {text}")
                    return "I encountered a system error while trying to do that."
                    
    except Exception as e:
        logging.error(f"Error executing remote tool {tool_name}: {e}")
        return "I'm sorry, I couldn't complete that action due to an error."


@function_tool()
async def schedule_meeting(
    context: RunContext, 
    title: str, 
    date: str, 
    time: str,
    attendee_email: Optional[str] = None
) -> str:
    """Schedule a meeting or appointment."""
    return await execute_remote_tool("schedule_meeting", {
        "title": title,
        "date": date,
        "time": time,
        "attendee_email": attendee_email
    })

@function_tool()
async def send_email(
    context: RunContext,
    to: str,
    subject: str,
    body: str
) -> str:
    """Send an email."""
    return await execute_remote_tool("send_email", {
        "to": to,
        "subject": subject,
        "body": body
    })

@function_tool()
async def send_whatsapp(
    context: RunContext,
    to: str,
    message: str
) -> str:
    """Send a WhatsApp message."""
    return await execute_remote_tool("send_whatsapp", {
        "to": to,
        "message": message
    })

@function_tool()
async def check_inventory(
    context: RunContext,
    product_name: str
) -> str:
    """Check product inventory and price."""
    result = await execute_remote_tool("check_inventory", {
        "product_name": product_name
    })
    # The API returns a dict, but execute_remote_tool returns a string message or success.
    # We might want to adjust execute_remote_tool to handle data returns better if we want the agent to read 50 items.
    # For now, let's assume the API returns a friendly 'message' or we rely on the generic success message.
    # Actually, check_inventory returns data. Let's handle it.
    
    # Re-implementing execute for this specifically because we need data, not just message
    try:
        ctx = get_job_context()
        metadata = json.loads(ctx.room.metadata or "{}")
        company_id = metadata.get("company_id")
        agent_id = metadata.get("agent_id")
        
        headers = {'Content-Type': 'application/json'}
        internal_token = os.getenv('INTERNAL_API_TOKEN')
        if internal_token:
            headers['X-Internal-Token'] = internal_token
            
        async with aiohttp.ClientSession() as session:
             async with session.post(f"{API_URL}/api/internal/execute-tool", json={
                "company_id": company_id, 
                "agent_id": agent_id,
                "tool_name": "check_inventory",
                "arguments": {"product_name": product_name}
             }, headers=headers) as response:
                 data = await response.json()
                 if data.get('success'):
                     return f"We have {data.get('quantity')} units of {data.get('product')} available at ${data.get('price')}."
                 else:
                     return "Item not found."
    except Exception as e:
        logging.error(f"Error in check_inventory: {e}")
        return "Could not check inventory."

@function_tool()
async def transfer_call(
    context: RunContext,
    reason: str,
    department: Optional[str] = None
) -> str:
    """Transfer the call to a human or another department."""
    return await execute_remote_tool("transfer_call", {
        "reason": reason,
        "department": department
    })

@function_tool()
async def create_payment_link(
    context: RunContext,
    amount: float,
    description: str
) -> str:
    """Create a payment link."""
    # Custom handling to read the link
    try:
        ctx = get_job_context()
        metadata = json.loads(ctx.room.metadata or "{}")
        
        headers = {'Content-Type': 'application/json'}
        internal_token = os.getenv('INTERNAL_API_TOKEN')
        if internal_token:
            headers['X-Internal-Token'] = internal_token
            
        async with aiohttp.ClientSession() as session:
             async with session.post(f"{API_URL}/api/internal/execute-tool", json={
                "company_id": metadata.get("company_id"), 
                "agent_id": metadata.get("agent_id"),
                "tool_name": "create_payment_link",
                "arguments": {"amount": amount, "description": description}
             }, headers=headers) as response:
                 data = await response.json()
                 if data.get('success'):
                     return f"I've generated a payment link for ${data.get('amount')}. It is {data.get('payment_link')}."
                 else:
                     return "Could not generate link."
    except Exception as e:
        logging.error(f"Error in create_payment_link: {e}")
        return "Error creating payment."

@function_tool()
async def consult_knowledge_base(
    context: RunContext,
    query: str
) -> str:
    """
    Search the company knowledge base (RAG) to find specific information to answer user questions.
    Use this whenever you need to know about company policies, products, services, or specific bio details.
    """
    # Use execute_remote_tool but mapped to a specific internal endpoint or just generic execute
    # Ideally we use the 'execute_remote_tool' helper which calls the 'execute-tool' endpoint.
    # The 'execute-tool' endpoint in voice_agent_api.py handles 'consult_knowledge_base' now.
    
    return await execute_remote_tool("consult_knowledge_base", {
        "query": query
    })
@function_tool()
async def end_call(
    context: RunContext,
    reason: str
) -> None:
    """
    End the current call gracefully after saying goodbye.
    Use this when: 
    - The conversation objective has been completed
    - The user says goodbye or indicates they want to end the call
    - The user asks to hang up
    
    Args:
        reason: Brief explanation of why the call is ending (e.g., "User confirmed meeting availability", "User declined", "User said goodbye")
    """
    logging.info(f"📞 Ending call. Reason: {reason}")
    
    try:
        # Get room info from job context
        job_ctx = get_job_context()
        if not job_ctx or not job_ctx.room:
            logging.error("No room context available")
            return None
            
        room_name = job_ctx.room.name
        
        # Find the SIP participant (phone participant)
        sip_participant = None
        for participant in job_ctx.room.remote_participants.values():
            # SIP participants typically have identity starting with 'phone-'
            if participant.identity.startswith('phone-') or 'sip' in participant.identity.lower():
                sip_participant = participant
                break
        
        if sip_participant:
            logging.info(f"📞 Removing SIP participant: {sip_participant.identity}")
            
            # Use LiveKit API to remove the participant (this hangs up the SIP call)
            from livekit.api import LiveKitAPI, RoomServiceClient
            
            livekit_api = LiveKitAPI()
            await livekit_api.room.remove_participant(
                room=room_name,
                identity=sip_participant.identity
            )
            await livekit_api.aclose()
            
            logging.info("✅ SIP participant removed - call hung up successfully.")
        else:
            logging.warning("No SIP participant found to remove")
            # Fallback: disconnect from room
            await job_ctx.room.disconnect()
            logging.info("✅ Room disconnected as fallback.")
            
        return None
        
    except Exception as e:
        logging.error(f"Error ending call: {e}")
        # Last resort fallback
        try:
            job_ctx = get_job_context()
            if job_ctx and job_ctx.room:
                await job_ctx.room.disconnect()
        except Exception as e2:
            logging.error(f"Fallback also failed: {e2}")
        return None
