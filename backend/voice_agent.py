"""
PymAI Voice Agent - Real-Time Voice with OpenAI Realtime API
Based on LiveKit Agents framework and reference project.
"""
import asyncio
import os
import json
import aiohttp
from datetime import datetime
from dotenv import load_dotenv

from livekit import agents, api
from livekit.agents import AgentSession, Agent, RoomInputOptions
from livekit.plugins import openai

import voice_tools 

# Try to import noise cancellation (optional)
try:
    from livekit.plugins import noise_cancellation
    HAS_NOISE_CANCELLATION = True
except ImportError:
    HAS_NOISE_CANCELLATION = False
    print("⚠️ noise_cancellation plugin not installed. Running without it.")

# Load environment variables
load_dotenv()

API_URL = os.getenv("PYMAI_API_URL", os.getenv("ONEPUNCH_API_URL", "http://localhost:5010"))

# Voice Mapping
VOICE_MAP = {
    "female": "coral",   # or shimmer, sage
    "male": "echo",      # or ash, ballad, verse
    "neutral": "alloy"
}

# Tool Mapping
TOOL_MAP = {
    'schedule_meeting': voice_tools.schedule_meeting,
    'send_email': voice_tools.send_email,
    'send_whatsapp': voice_tools.send_whatsapp,
    'check_inventory': voice_tools.check_inventory,
    'transfer_call': voice_tools.transfer_call,
    'create_payment_link': voice_tools.create_payment_link,
    'process_payment': voice_tools.create_payment_link, # Alias
    'consult_knowledge_base': voice_tools.consult_knowledge_base,
    'end_call': voice_tools.end_call  # Allow agent to hang up
}

async def fetch_agent_context(company_id, agent_id, query=None):
    """Fetch agent context from internal API"""
    if not company_id:
        return None
        
    try:
        url = f"{API_URL}/api/internal/voice-context/{company_id}/{agent_id or 0}"
        params = {}
        if query:
            params['rag_query'] = query
        
        # Include internal API token for authentication
        headers = {}
        internal_token = os.getenv('INTERNAL_API_TOKEN')
        if internal_token:
            headers['X-Internal-Token'] = internal_token
            
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    text = await response.text()
                    print(f"❌ Error fetching context: {text}")
                    return None
    except Exception as e:
        print(f"❌ Exception fetching context: {e}")
        return None

async def entrypoint(ctx: agents.JobContext):
    """
    Entrypoint for the Voice Agent.
    """
    # Validate API keys
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ ERROR: OPENAI_API_KEY is missing. Voice Agent cannot start.")
        return
    
    # 1. Fast Metadata Check (Non-blocking)
    metadata = {}
    raw_metadata = ctx.room.metadata
    
    # Try to parse existing metadata immediately
    if raw_metadata:
        try:
            metadata = json.loads(raw_metadata)
        except:
            print(f"⚠️ Could not parse room metadata: {raw_metadata}")

    # Prepare initial values (checking metadata if available)
    initial_gender = metadata.get('gender', 'neutral').lower()
    initial_voice = VOICE_MAP.get(initial_gender, 'alloy')
    
    print(f"DEBUG: Initial Voice Selection: {initial_voice} (Gender: {initial_gender})")

    # 2. Start Session IMMEDIATELY with Filler (Zero Latency)
    # This prevents timeouts and ensures user hears audio ASAP
    
    filler_instructions = (
        "You are a human-like assistant. "
        "Your Immediate Goal: Say a natural, generic greeting to check if the user is there. "
        "Say ONLY: '¿Hola? ¿Buenas tardes?' "
        "Then wait quietly. Do NOT say you are loading anything. Just act like a human waiting for the other person to answer."
    )
    
    session = AgentSession(
        llm=openai.realtime.RealtimeModel(
            voice=initial_voice, 
            model="gpt-4o-realtime-preview", 
            temperature=0.7,
        )
    )
    
    if HAS_NOISE_CANCELLATION:
        room_input = RoomInputOptions(
            noise_cancellation=noise_cancellation.BVCTelephony(),
        )
    else:
        room_input = RoomInputOptions()

    # Generic Agent Wrapper
    # STRATEGY CHANGE: We load ALL tools initially because we can't easily add them later.
    # The agent will only use them if instructed/relevant.
    # We use a set to avoid duplicate tools (aliases in TOOL_MAP) which cause LiveKit "duplicate function name" error
    all_tools = list(set(TOOL_MAP.values()))
    
    agent = Agent(
        instructions=filler_instructions,
        tools=all_tools 
    )
    
    # Start Session NOW
    await session.start(
        room=ctx.room,
        agent=agent,
        room_input_options=room_input,
    )
    
    print("DEBUG: Session started (Filler Mode).")
    
    # Trigger Filler Audio Immediately
    await session.generate_reply()
    
    # --- BACKGROUND OPERATIONS ---
    # Now we can safely do heavy lifting without blocking call pickup
    
    # 3. Robust Metadata Fetch (if missing)
    if not raw_metadata:
        print("⚠️ Local metadata empty. Fetching from LiveKit API in background...")
        try:
            lk_url = os.getenv("LIVEKIT_URL")
            lk_key = os.getenv("LIVEKIT_API_KEY")
            lk_secret = os.getenv("LIVEKIT_API_SECRET")
            
            if lk_url and lk_key and lk_secret:
                lk_api = api.LiveKitAPI(lk_url, lk_key, lk_secret)
                rooms = await lk_api.room.list_rooms(api.ListRoomsRequest(names=[ctx.room.name]))
                if rooms.rooms:
                    raw_metadata = rooms.rooms[0].metadata
                    print(f"✅ Fetched metadata from API: {raw_metadata}")
                    # Parse again
                    try:
                        metadata = json.loads(raw_metadata)
                    except:
                        pass
                await lk_api.aclose()
        except Exception as e:
            print(f"❌ Error fetching metadata from API: {e}")
            
    print(f"DEBUG: Final Room Metadata: '{raw_metadata}'")

    company_id = metadata.get('company_id')
    agent_id = metadata.get('agent_id')
    purpose = metadata.get('purpose')
    
    print(f"DEBUG: New Session | Company: {company_id} | Agent: {agent_id}")
    if purpose:
        print(f"DEBUG: Call Purpose: {purpose}")
    
    print("DEBUG: Loading full context in background...")
    
    # 3. Fetch Dynamic Context (using purpose as RAG query)
    context = await fetch_agent_context(company_id, agent_id, query=purpose)
    
    tools_whitelist = []
    # Initialize final_instructions with a safe default
    final_instructions = "You are a helpful assistant. Speak Spanish."
    
    if context:
        print(f"DEBUG: Loaded context for agent '{context.get('agent_name')}'")
        
        # Map Voice (Logic restored for Context, even if we can't change audio timbre mid-session)
        gender = context.get('gender', 'neutral').lower()
        # Voice selection 'voice = VOICE_MAP...' is skipped because session is already active with 'alloy'.
        # We will enforce gender via instructions instead.
        
        # Set Instructions
        # Use context instructions if available, otherwise keep default
        final_instructions = context.get('instructions', final_instructions)
        
        # Add RAG Context if available
        # Add Basic Company Info ONLY (not full RAG dump)
        # We rely on the tool 'consult_knowledge_base' for detailed queries.
        # But we can inject the 'agent_name' and 'company_name' into instructions.
        
        # Note: We removed the massive RAG injection loop to save context.
        # Ensure instructions tell the agent to use the tool.
        final_instructions += "\n\nIMPORTANT: You have access to a 'consult_knowledge_base' tool. Use it immediately if the user asks a question about the company, services, or policies that you don't know."
        
        # Capture Enabled Tools for Whitelist
        enabled_tool_names = context.get('enabled_tools', [])
        tools_whitelist = [name for name in enabled_tool_names if name in TOOL_MAP]
        print(f"DEBUG: Authorized tools: {tools_whitelist}")

    else:
        print("⚠️ No context loaded, using defaults.")

    # 4. Inject Specific Call Purpose (if any)
    if purpose:
        final_instructions += f"""

# PRIORITY MISSION (OVERRIDE ALL ELSE)
Your SOLE GOAL right now is: {purpose}

## Protocol:
1. Introduce yourself briefly (Name/Company).
2. STATE THE PURPOSE IMMEDIATELY.
3. Do NOT ask 'How can I help?'. Do NOT be generic.
4. Listen for the response and get an answer regarding the purpose.
5. If interrupted, acknowledge briefly, then RETURN TO THE PURPOSE.

## CALL ENDING (CRITICAL):
You MUST use the 'end_call' tool to terminate the call when:
- ✅ The objective has been COMPLETED (e.g., user confirmed their availability, meeting scheduled)
- ✅ User says goodbye, "adiós", "hasta luego", "gracias, eso es todo"
- ✅ User clearly indicates they want to end (e.g., "ok, eso es todo", "perfecto, hablamos luego")
- ✅ You have confirmed the next steps and there's nothing more to discuss
- ❌ Do NOT keep talking after the objective is complete - close the call professionally

When ending, say a brief farewell like "Perfecto, gracias por su tiempo. ¡Hasta pronto!" and then IMMEDIATELY use 'end_call'.
"""

    # --- CRITICAL FIX: Create new Agent with full instructions and swap it in ---
    # This ensures the purpose is PERSISTED in the agent's core for the entire call.
    print("DEBUG: Creating new agent with full purpose-driven instructions...")
    
    # Get all tools (same as before)
    all_tools = list(set(TOOL_MAP.values()))
    
    # Create a new Agent with the COMPLETE instructions (including purpose)
    purpose_agent = Agent(
        instructions=final_instructions,
        tools=all_tools
    )
    
    # Swap the agent in the session
    print("DEBUG: Swapping to purpose-driven agent...")
    session.update_agent(purpose_agent)
    
    # --- BUILD TRANSITION PROMPT ---
    print("DEBUG: Generating purpose-driven greeting...")
    
    # We construct a whitelist string
    allowed_tools_str = ", ".join(tools_whitelist) if tools_whitelist else "None"
    
    transition_prompt = (
        f"CONTEXT UPDATE: You are on an outbound call to {metadata.get('destination', 'the user')}.\n"
        f"YOUR PURPOSE: {purpose}\n\n"
        f"SPEAK NOW:\n"
        f"1. Greet briefly and introduce yourself.\n"
        f"2. State your purpose clearly: '{purpose}'\n"
        f"3. Wait for their response.\n"
        f"DO NOT ask generic questions. Be direct and professional."
    )
    
    # Generate the purpose-driven opening
    await session.generate_reply(
        instructions=transition_prompt
    )
    
    # --- TRANSCRIPT CAPTURE ---
    # Build transcript using multiple events
    transcript_lines = []
    call_start_time = datetime.now()
    
    @session.on("user_input_transcribed")
    def on_user_speech(ev):
        """Capture user speech"""
        try:
            text = ev.transcript if hasattr(ev, 'transcript') else str(ev)
            if text and text.strip():
                transcript_lines.append(f"User: {text}")
                print(f"TRANSCRIPT [User]: {text[:50]}...")
        except Exception as e:
            print(f"DEBUG: Error capturing user speech: {e}")
    
    @session.on("agent_speech_committed")
    def on_agent_speech(ev):
        """Capture agent speech"""
        try:
            text = ev.content if hasattr(ev, 'content') else str(ev)
            if text and text.strip():
                transcript_lines.append(f"Agent: {text}")
                print(f"TRANSCRIPT [Agent]: {text[:50]}...")
        except Exception as e:
            print(f"DEBUG: Error capturing agent speech: {e}")
    
    # --- REPORTING HOOK ---
    # Wait for session to close (more reliable than room disconnect)
    session_closed_event = asyncio.Event()
    
    @session.on("close")
    def on_session_close(ev=None):
        print("DEBUG: Session close event received.")
        session_closed_event.set()
    
    # Also listen to room disconnect as backup
    @ctx.room.on("disconnected")
    def on_room_disconnect(ev=None):
        print("DEBUG: Room disconnect event received.")
        session_closed_event.set()
    
    await session_closed_event.wait()
    call_end_time = datetime.now()
    call_duration = int((call_end_time - call_start_time).total_seconds())
    print(f"DEBUG: Session ended. Call duration: {call_duration}s. Generating report...")
    
    # Generate Report
    try:
        # Build transcript from captured items
        transcript = "\n".join(transcript_lines) if transcript_lines else "No transcript available."
        print(f"DEBUG: Transcript length: {len(transcript)} chars, {len(transcript_lines)} lines")
        
        # Generate human-friendly summary using LLM
        summary = transcript  # Default fallback
        if transcript_lines and transcript != "No transcript available.":
            try:
                # Import OpenAI client library locally to avoid conflict with livekit plugin
                # Rename it to avoid shadowing the global 'openai' from livekit.plugins
                import openai as openai_lib
                openai_client = openai_lib.AsyncOpenAI()
                
                summary_prompt = f"""Eres un asistente que resume llamadas telefónicas para administradores.
Genera un resumen breve y profesional (máximo 3-4 oraciones) de la siguiente conversación telefónica.
Incluye: objetivo de la llamada, resultado, y cualquier acción pendiente.

Propósito de la llamada: {purpose}
Destino: {metadata.get('destination', 'Desconocido')}
Duración: {call_duration} segundos

Transcripción:
{transcript}

Resumen (en español, natural, como si fuera un reporte para un jefe):"""

                llm_response = await openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": summary_prompt}],
                    max_tokens=200,
                    temperature=0.7
                )
                summary = llm_response.choices[0].message.content.strip()
                print(f"DEBUG: LLM Summary generated: {summary[:100]}...")
            except Exception as llm_error:
                print(f"DEBUG: LLM summary failed, using transcript: {llm_error}")
                summary = f"Transcripción de la llamada:\\n{transcript}"
        
        # Send to Internal API
        url = f"{API_URL}/api/internal/report-call"
        headers = {}
        internal_token = os.getenv('INTERNAL_API_TOKEN')
        if internal_token:
            headers['X-Internal-Token'] = internal_token
            
        payload = {
            "company_id": company_id,
            "agent_id": agent_id,
            "destination": metadata.get('destination', 'Unknown'),
            "duration": call_duration,
            "summary": summary
        }
        
        async with aiohttp.ClientSession() as http_session:
            async with http_session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    print("✅ Call report sent successfully.")
                else:
                    text = await response.text()
                    print(f"❌ Error sending report: {text}")
                    
    except Exception as e:
        print(f"❌ Error generating report: {e}")

if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
