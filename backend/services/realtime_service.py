"""
Realtime Service - Handles Redis Pub/Sub coordination and Socket.IO broadcasting.
"""
import json
import logging
import asyncio
import redis
from config import get_config
from extensions import socketio

logger = logging.getLogger(__name__)
config = get_config()

# Parse redis URL from Celery broker URL
REDIS_URL = config.CELERY_BROKER_URL or "redis://localhost:6380/0"

class RealtimeService:
    _redis_sync_client = None

    @classmethod
    def get_sync_client(cls):
        """Get or create synchronous Redis client for publishing."""
        if cls._redis_sync_client is None:
            try:
                cls._redis_sync_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
            except Exception as e:
                logger.error(f"Failed to connect to Redis at {REDIS_URL}: {e}")
        return cls._redis_sync_client

    @classmethod
    def publish_lead_update(cls, company_id: int, customer_id: int, update_data: dict):
        """
        Publish a lead update event to the Redis channel crm_pipeline.
        """
        client = cls.get_sync_client()
        if not client:
            return

        payload = {
            "company_id": company_id,
            "type": "LEAD_UPDATED",
            "data": {
                "contact_id": customer_id,
                **update_data
            }
        }
        
        try:
            client.publish("crm_pipeline", json.dumps(payload))
            logger.info(f"Published lead update to Redis: {payload}")
        except Exception as e:
            logger.error(f"Failed to publish lead update to Redis: {e}")

    @classmethod
    def publish_conversation_update(cls, company_id: int, conversation_id: int, update_data: dict):
        """
        Publish a conversation status update (e.g. resolved/assigned) to Redis.
        """
        client = cls.get_sync_client()
        if not client:
            return

        payload = {
            "company_id": company_id,
            "type": "CONVERSATION_UPDATED",
            "data": {
                "conversation_id": conversation_id,
                **update_data
            }
        }
        
        try:
            client.publish("crm_pipeline", json.dumps(payload))
            logger.info(f"Published conversation update to Redis: {payload}")
        except Exception as e:
            logger.error(f"Failed to publish conversation update to Redis: {e}")


# --- Background Async Listener for Redis Pub/Sub ---

async def start_redis_listener():
    """
    Subscribes to crm_pipeline channel in Redis and broadcasts events 
    to corresponding python-socketio rooms.
    Uses pubsub.get_message() with timeout to avoid 'aclose() asynchronous generator is already running'
    and un-awaited coroutine issues during FastAPI shutdown or restarts.
    """
    import redis.asyncio as async_redis
    logger.info(f"Initializing Async Redis Listener on {REDIS_URL}...")
    
    while True:
        client = None
        pubsub = None
        try:
            client = async_redis.Redis.from_url(REDIS_URL, decode_responses=True)
            pubsub = client.pubsub()
            await pubsub.subscribe("crm_pipeline")
            logger.info("Successfully subscribed to Redis 'crm_pipeline' channel.")
            
            while True:
                try:
                    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if message and message.get("type") == "message":
                        try:
                            payload = json.loads(message["data"])
                            company_id = payload.get("company_id")
                            event_type = payload.get("type")
                            event_data = payload.get("data")
                            
                            if company_id and event_type:
                                room = f"company_room_{company_id}"
                                socketio.emit(event_type, event_data, room=room)
                                logger.info(f"Broadcasted event '{event_type}' to Socket.IO room '{room}'")
                        except Exception as parse_err:
                            logger.error(f"Error parsing Redis message data: {parse_err}")
                except asyncio.CancelledError:
                    raise
                except Exception as inner_err:
                    logger.warning(f"Error reading message from Redis pubsub: {inner_err}")
                    await asyncio.sleep(1)
                    break
                    
        except asyncio.CancelledError:
            logger.info("Redis listener task cancelled.")
            break
        except Exception as err:
            logger.error(f"Redis Pub/Sub connection error: {err}. Retrying in 5 seconds...")
        finally:
            if pubsub is not None:
                try:
                    await pubsub.unsubscribe("crm_pipeline")
                except Exception:
                    pass
                try:
                    await pubsub.aclose()
                except Exception:
                    pass
            if client is not None:
                try:
                    await client.aclose()
                except Exception:
                    pass
        
        await asyncio.sleep(5)


