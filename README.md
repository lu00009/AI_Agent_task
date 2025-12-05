# AI Agent Task

A FastAPI app that parses resumes with Gemini, extracts skills, and recommends jobs using Tavily search. Includes a light-mode web UI with chat.

## Features
- Upload PDF/TXT resumes and extract structured data
- Persist skills and search job leads
- Chat assistant that formats job lists with real links
- Simple light-mode UI

## Requirements
- Python 3.11+
- API keys:
  - GEMINI_API_KEY
  - TAVILY_API_KEY

## Setup
1. Create and fill .env:
   ```
   GEMINI_API_KEY=your_key
   TAVILY_API_KEY=your_key
   TAVILY_BASE_URL=
   GEMINI_MODEL=gemini-1.5-pro
   ```
2. Install dependencies:
   ```
   pip install fastapi uvicorn google-generativeai tavily-python python-dotenv pypdf
   ```

## Run
```
uvicorn Resume_parser.extract:app --reload
```
Open http://localhost:8000

## Project Structure
- Resume_parser/
  - routes/route.py: API endpoints
  - ui/: Static HTML/JS/CSS
  - config/settings.py: Env & config
  - schema/resume.py: TypedDicts
- Job_Hunter/: legacy helpers

## Notes
- Ensure .env is present before starting
- If Tavily returns 403, app falls back to role recommendations without links
- Chat output uses numbered multi-line items: Title, Location, Link, Info
