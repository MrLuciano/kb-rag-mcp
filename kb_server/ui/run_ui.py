#!/usr/bin/env python3
"""
Startup script for KB-RAG Web UI server.

Runs FastAPI application with Uvicorn.
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import routes to register them with the app
from kb_server.ui import routes  # noqa: F401
from kb_server.ui.app import app

if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("UI_HOST", "0.0.0.0")
    port = int(os.getenv("UI_PORT", "8001"))
    
    print(f"Starting KB-RAG Web UI on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )
