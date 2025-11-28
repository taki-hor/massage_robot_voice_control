#!/usr/bin/env python3
"""
Entry point for UR10e Voice-Controlled Massage System Server
Run with: python run.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import uvicorn

def main():
    """Start the server"""
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    reload = os.environ.get("RELOAD", "false").lower() == "true"

    print(f"Starting UR10e Voice Massage Control Server...")
    print(f"Server: http://{host}:{port}")
    print(f"API Docs: http://{host}:{port}/docs")
    print()

    uvicorn.run(
        "server.main:app",
        host=host,
        port=port,
        reload=reload,
    )

if __name__ == "__main__":
    main()
