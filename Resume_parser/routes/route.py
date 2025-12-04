from fastapi import APIRouter, UploadFile, File, HTTPException
import json
import google.generativeai as genai
from tavily import TavilyClient
from tavily.errors import ForbiddenError
from pydantic import BaseModel
import uuid
import io
import os
from typing import TypedDict

from Resume_parser.config.settings import GEMINI_MODEL, TAVILY_API_KEY, TAVILY_BASE_URL
from Resume_parser.gemini import configure_genai
from Resume_parser.schema.resume import ResumeData, ExperienceItem, EducationItem

# Configure Gemini and Tavily
configure_genai()

# Initialize Tavily client
if not TAVILY_API_KEY:
    raise RuntimeError("TAVILY_API_KEY is not set. Add it to your .env or export it in your shell.")

tavily = TavilyClient(api_key=TAVILY_API_KEY, base_url=TAVILY_BASE_URL) if TAVILY_BASE_URL else TavilyClient(api_key=TAVILY_API_KEY)

router = APIRouter()

# In-memory stores
LAST_SKILLS: list[str] = []
SESSIONS: dict[str, list[dict]] = {}

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None

# PDF extraction
def _extract_text_from_pdf_bytes(data: bytes) -> str:
    try:
        import pypdf  # type: ignore
        reader = pypdf.PdfReader(io.BytesIO(data))
        pieces: list[str] = []
        for page in reader.pages:
            try:
                pieces.append(page.extract_text() or "")
            except Exception:
                continue
        return "\n".join(pieces).strip()
    except Exception:
        try:
            return data.decode("utf-8", errors="replace")
        except Exception:
            return ""

structured_model = genai.GenerativeModel(
    GEMINI_MODEL,
    generation_config={
        "response_mime_type": "application/json",
        "response_schema": ResumeData,
    },
)

@router.post("/extract")
async def extract_resume(file: UploadFile = File(...)):
    try:
        content_bytes = await file.read()
        resume_text = (
            _extract_text_from_pdf_bytes(content_bytes)
            if content_bytes[:5] == b"%PDF-" else content_bytes.decode("utf-8", errors="replace")
        )
        resume_text = "\n".join(line.strip() for line in resume_text.splitlines())
        instruction = (
            "Parse the following resume into the schema fields (name, skills[], experience[{company, role, duration, description}], "
            "education[{institution, degree, year}]). Return valid JSON only. For skills, return concise skill keywords.\n\n"
            "Resume:\n"
        )
        response = structured_model.generate_content(instruction + resume_text)
        data = json.loads(response.text)
        global LAST_SKILLS
        LAST_SKILLS = data.get("skills", []) or []
        return data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/skills")
async def skills():
    return {"skills": LAST_SKILLS}

def search_jobs(skills: list[str]):
    query = (
        "jobs hiring now for (" + " ".join(skills) + ") "
        "site:linkedin.com OR site:ethiojobs.net OR site:remoteok.com"
    )
    try:
        return tavily.search(query=query)
    except ForbiddenError:
        raise HTTPException(status_code=403, detail="Tavily API key invalid or missing. Set TAVILY_API_KEY.")

@router.get("/jobs")
async def jobs():
    if not LAST_SKILLS:
        raise HTTPException(status_code=400, detail="No skills found. Upload a resume first.")
    try:
        search_result = search_jobs(LAST_SKILLS)
    except HTTPException as e:
        if e.status_code == 403:
            rec_model = genai.GenerativeModel(GEMINI_MODEL)
            prompt = (
                "Recommend 5 job roles for the user based on these skills. "
                "For each, include a short reason. Return JSON: recommendations: [{title, reason}].\n\n"
                f"User skills: {json.dumps(LAST_SKILLS)}"
            )
            resp = rec_model.generate_content(prompt)
            try:
                return {"skills": LAST_SKILLS, "recommendations": json.loads(resp.text).get("recommendations", [])}
            except Exception:
                return {"skills": LAST_SKILLS, "text": resp.text}
        else:
            raise
    rec_model = genai.GenerativeModel(GEMINI_MODEL)
    prompt = (
        "You are a helpful job assistant. Given the user's skills and search results, "
        "recommend 5 roles with short reasons and include links if available.\n\n"
        f"User skills: {json.dumps(LAST_SKILLS)}\n\n"
        f"Search results: {json.dumps(search_result)}\n\n"
        "Return JSON with fields: recommendations: [{title, company?, link?, reason}]."
    )
    resp = rec_model.generate_content(prompt)
    try:
        return json.loads(resp.text)
    except Exception:
        return {"skills": LAST_SKILLS, "search": search_result, "text": resp.text}

@router.post("/chat")
async def chat(req: ChatRequest):
    if not LAST_SKILLS:
        raise HTTPException(status_code=400, detail="No skills found. Upload a resume first.")

    session_id = req.session_id or str(uuid.uuid4())
    history = SESSIONS.setdefault(session_id, [])

    planner = genai.GenerativeModel(GEMINI_MODEL)
    plan_prompt = (
        "You are an assistant that decides if a web job search is needed.\n"
        f"User message: {req.message}\n"
        f"Known user skills: {json.dumps(LAST_SKILLS)}\n\n"
        "If search will improve the answer, return ONLY JSON like: {\"tool\":\"search_jobs\", \"query\": \"extra keywords if any\"}.\n"
        "Otherwise return ONLY JSON like: {\"answer\": \"short helpful reply\"}.\n"
        "No prose. JSON only."
    )
    plan_raw = planner.generate_content(plan_prompt).text
    try:
        plan = json.loads(plan_raw)
    except Exception:
        plan = {"answer": plan_raw}

    if plan.get("tool") == "search_jobs":
        extra = plan.get("query") or ""
        try:
            sr = search_jobs(LAST_SKILLS + ([extra] if extra else []))
        except HTTPException as e:
            if e.status_code == 403:
                sr = None
            else:
                raise
        responder = genai.GenerativeModel(GEMINI_MODEL)
        prompt = (
            "Chat with the user and suggest concrete job leads. Be concise and friendly.\n"
            f"User message: {req.message}\n"
            f"User skills: {json.dumps(LAST_SKILLS)}\n"
            f"Search results: {json.dumps(sr) if sr is not None else 'unavailable'}\n\n"
            "Return JSON only with: {\"text\": string, \"recommendations\": [{title, company?, link?, reason}]}."
            "Ensure recommendations is a list of 5 items and keep reasons short."
        )
        resp = responder.generate_content(prompt)
        try:
            out = json.loads(resp.text)
        except Exception:
            out = {"text": resp.text}
    else:
        direct = genai.GenerativeModel(GEMINI_MODEL)
        prompt = (
            "Reply helpfully to the user about job search based on their skills.\n"
            f"User message: {req.message}\n"
            f"User skills: {json.dumps(LAST_SKILLS)}\n\n"
            "Return JSON only with: {\"text\": string, \"recommendations\": [{title, company?, link?, reason}]}."
            "Ensure recommendations is a list of up to 5 items and keep reasons short."
        )
        dresp = direct.generate_content(prompt)
        try:
            out = json.loads(dresp.text)
        except Exception:
            out = {"text": dresp.text}

    history.append({"role": "user", "content": req.message})
    history.append({"role": "assistant", "content": out.get("text", "")})
    if len(history) > 20:
        SESSIONS[session_id] = history[-20:]

    out["session_id"] = session_id
    return out

@router.get("/health")
async def health():
    return {"status": "ok"}
