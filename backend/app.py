"""
PymAI - Deprecated Flask App Entry Point
Provides a minimal self-contained mock application factory to satisfy 
legacy celery task context imports without importing Flask.

Copyright © 2026 WEBLIFETECH (Jonnathan Peña). All Rights Reserved.
"""

class AppContextMock:
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

class FlaskMock:
    def __init__(self, name=None, **kwargs):
        self.name = name
        self.config = {}
        
    def app_context(self):
        return AppContextMock()

def create_app(config_class=None):
    """Minimal self-contained application factory returning a dummy mock app"""
    return FlaskMock(__name__)

app = create_app()
