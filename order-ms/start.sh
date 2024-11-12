#!/bin/sh
# Run Faust worker and FastAPI app concurrently

faust -A main:faustApp worker &  # Start Faust worker in the background
uvicorn main:app --host 0.0.0.0 --port 8000 --reload  # Start FastAPI app