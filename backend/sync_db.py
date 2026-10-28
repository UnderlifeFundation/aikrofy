#!/usr/bin/env python3
"""
Convenience entry point for database synchronization.
Usage: python sync_db.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scripts.sync_db_schema import sync_database_schema

if __name__ == '__main__':
    success = sync_database_schema(verbose=True)
    sys.exit(0 if success else 1)
