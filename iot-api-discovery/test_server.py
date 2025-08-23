#!/usr/bin/env python3
"""
Simple test script to start the server and see any error messages.
"""

import uvicorn
import sys
import traceback

try:
    print("Starting server...")
    uvicorn.run("api.server:app", host="127.0.0.1", port=8000, log_level="debug")
except Exception as e:
    print(f"Error starting server: {e}")
    traceback.print_exc()
    sys.exit(1)
