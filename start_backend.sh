#!/bin/bash
cd /Users/abhishek/CascadeProjects/document-ai-rpa
source backend/venv/bin/activate
export PYTHONPATH=/Users/abhishek/CascadeProjects/document-ai-rpa/backend:$PYTHONPATH
uvicorn backend.app.main:app --reload --port 8000