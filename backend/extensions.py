"""
Extensions module - Pure FastAPI & SQLAlchemy 2.0 version
Separates database and other extensions from app to avoid circular imports
"""
import sys
import asyncio
import contextvars
from types import ModuleType
import sqlalchemy as sa
from sqlalchemy.orm import relationship, backref
from database import Base, db_session
import socketio as pysocketio

class SQLAlchemyMock:
    Model = Base
    session = db_session
    
    # Types
    Column = sa.Column
    Integer = sa.Integer
    String = sa.String
    Text = sa.Text
    Boolean = sa.Boolean
    DateTime = sa.DateTime
    ForeignKey = sa.ForeignKey
    Enum = sa.Enum
    JSON = sa.JSON
    Float = sa.Float
    Table = sa.Table
    Numeric = sa.Numeric
    TIMESTAMP = sa.TIMESTAMP
    Time = sa.Time
    
    # Constraints & Indexes
    UniqueConstraint = sa.UniqueConstraint
    Index = sa.Index
    CheckConstraint = sa.CheckConstraint
    ForeignKeyConstraint = sa.ForeignKeyConstraint
    PrimaryKeyConstraint = sa.PrimaryKeyConstraint
    event = sa.event
    
    # Relationships
    relationship = staticmethod(relationship)
    backref = staticmethod(backref)
    
    # Utilities
    func = sa.func
    text = staticmethod(sa.text)

    # Metadata
    metadata = Base.metadata

    def init_app(self, *args, **kwargs):
        pass

db = SQLAlchemyMock()

# --- Socket.IO Integration for ASGI ---
sio = pysocketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
_sid_var = contextvars.ContextVar('sio_sid', default=None)
_main_loop = None

def set_main_loop(loop):
    global _main_loop
    _main_loop = loop

# Mock flask_socketio module
flask_socketio_mock = ModuleType('flask_socketio')

def emit(event, data=None, room=None, **kwargs):
    # Convert room parameter to 'to' for python-socketio
    global _main_loop
    try:
        current_loop = asyncio.get_running_loop()
    except RuntimeError:
        current_loop = None

    if current_loop is not None and current_loop.is_running():
        current_loop.create_task(sio.emit(event, data, to=room, **kwargs))
    elif _main_loop and _main_loop.is_running():
        asyncio.run_coroutine_threadsafe(sio.emit(event, data, to=room, **kwargs), _main_loop)
    else:
        try:
            asyncio.run(sio.emit(event, data, to=room, **kwargs))
        except Exception:
            pass

def join_room(room, sid=None, namespace=None):
    if sid is None:
        sid = _sid_var.get()
    if sid:
        global _main_loop
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        if current_loop is not None and current_loop.is_running():
            current_loop.create_task(sio.enter_room(sid, room, namespace=namespace))
        elif _main_loop and _main_loop.is_running():
            asyncio.run_coroutine_threadsafe(sio.enter_room(sid, room, namespace=namespace), _main_loop)
        else:
            try:
                asyncio.run(sio.enter_room(sid, room, namespace=namespace))
            except Exception:
                pass

flask_socketio_mock.emit = emit
flask_socketio_mock.join_room = join_room
flask_socketio_mock.set_main_loop = set_main_loop
sys.modules['flask_socketio'] = flask_socketio_mock

class SocketIOMock:
    def on(self, event):
        def decorator(f):
            @sio.on(event)
            async def wrapper(sid, data=None):
                _sid_var.set(sid)
                if asyncio.iscoroutinefunction(f):
                    await f(data)
                else:
                    f(data)
            return f
        return decorator
        
    def emit(self, event, data, room=None, **kwargs):
        emit(event, data, room=room, **kwargs)

socketio = SocketIOMock()

# Placeholders to prevent import errors during migration
class FakeExtension:
    def init_app(self, *args, **kwargs):
        pass

jwt = FakeExtension()
migrate = FakeExtension()
