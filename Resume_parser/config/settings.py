import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
TAVILY_BASE_URL = os.getenv("TAVILY_BASE_URL")
