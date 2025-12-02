# C:\Backend\main.py
import os
import re
import json
import requests
from datetime import datetime
from typing import Optional, Dict, Any, Generator, List

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, DateTime, JSON, ForeignKey
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session

# -------------------------
# Load env
# -------------------------
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")  # optional; if present, real Groq used
# If DATABASE_URL missing, stop early with helpful message
if not DATABASE_URL:
    raise SystemExit("ERROR: Please set DATABASE_URL in .env (example: postgresql://user:pass@localhost:5432/dbname)")

USE_REAL_GROQ = bool(GROQ_API_KEY)

# -------------------------
# DB / Models
# -------------------------
Base = declarative_base()

class HCP(Base):
    __tablename__ = "hcp"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    speciality = Column(String(255))
    organisation = Column(String(255))
    contact = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Interaction(Base):
    __tablename__ = "interaction"
    id = Column(Integer, primary_key=True, index=True)
    hcp_id = Column(Integer, ForeignKey("hcp.id"), nullable=True)
    rep_id = Column(String(128), default="rep_santosh")
    mode = Column(String(16), nullable=False, default="form")  # 'form' | 'chat'
    raw_text = Column(Text, nullable=True)
    form_data = Column(JSON, nullable=True)
    summary = Column(Text, nullable=True)
    topics = Column(JSON, nullable=True)
    sentiment = Column(String(32), nullable=True)
    materials_shared = Column(JSON, nullable=True)
    followups = Column(JSON, nullable=True)
    llm_meta = Column(JSON, nullable=True)
    status = Column(String(16), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    hcp = relationship("HCP", backref="interactions")


# Create engine & session
engine = create_engine(DATABASE_URL, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

# create tables
Base.metadata.create_all(bind=engine)

# -------------------------
# FastAPI app
# -------------------------
app = FastAPI(title="AI-First CRM HCP Module - Backend (single-file)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# DB dependency
# -------------------------
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -------------------------
# Pydantic schemas
# -------------------------
class HcpCreate(BaseModel):
    name: str
    speciality: Optional[str] = None
    organisation: Optional[str] = None
    contact: Optional[Dict[str, Any]] = None

class InteractionCreate(BaseModel):
    hcp_id: Optional[int] = None
    rep_id: str
    mode: str  # 'form' or 'chat'
    raw_text: Optional[str] = None
    form_data: Optional[Dict[str, Any]] = None

class InteractionEdit(BaseModel):
    updates: Dict[str, Any]

# -------------------------
# Utility: Groq chat call helper (simple REST)
# -------------------------
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

def call_groq_chat(system_prompt: str, user_prompt: str, model: str = "gemma2-9b-it", max_tokens: int = 512, temperature: float = 0.0) -> Dict[str, Any]:
    """
    Simple REST wrapper for Groq chat completions.
    Requires GROQ_API_KEY in env to run; otherwise raises ValueError.
    Returns dict with keys: raw (full response), text (assistant text).
    """
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not set in environment")

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    resp = requests.post(GROQ_API_URL, json=body, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    # parse text from choices
    text = ""
    try:
        choices = data.get("choices", [])
        if choices:
            msg = choices[0].get("message") or choices[0].get("delta") or choices[0]
            if isinstance(msg, dict):
                text = msg.get("content") or msg.get("text") or ""
            else:
                text = str(msg)
    except Exception:
        text = ""
    return {"raw": data, "text": text}

# -------------------------
# Text utilities for mock processing
# -------------------------
STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "in", "on", "with", "to", "for", "is", "was", "were", "it", "that", "this"
}

def simple_extract_topics(text: str, max_topics: int = 6):
    if not text:
        return []
    words = re.findall(r"\b[^\d\W]{3,}\b", text.lower())  # words >=3 letters
    filtered = [w for w in words if w not in STOPWORDS]
    seen = set()
    topics = []
    for w in filtered:
        if w in seen:
            continue
        seen.add(w)
        topics.append(w)
        if len(topics) >= max_topics:
            break
    return topics

def simple_sentiment(text: str):
    if not text:
        return "neutral"
    text_l = text.lower()
    positive = ["good", "great", "positive", "promising", "interested", "approve", "yes", "will"]
    negative = ["bad", "negative", "declined", "not", "no", "concern", "concerns", "problem", "refused"]
    score = 0
    for p in positive:
        if p in text_l:
            score += 1
    for n in negative:
        if n in text_l:
            score -= 1
    if score > 0:
        return "positive"
    if score < 0:
        return "negative"
    return "neutral"

# -------------------------
# Mock processor (fallback)
# -------------------------
def mock_process_interaction(interaction_id: int):
    db = SessionLocal()
    try:
        inter = db.query(Interaction).filter(Interaction.id == interaction_id).first()
        if not inter:
            return
        # Build summary from raw_text or form_data
        if inter.raw_text and inter.raw_text.strip():
            summary_text = inter.raw_text.strip()
            if len(summary_text) > 500:
                summary_text = summary_text[:497] + "..."
        elif inter.form_data and isinstance(inter.form_data, dict):
            fd = inter.form_data
            topic = fd.get("topic") or fd.get("subject") or ""
            materials = fd.get("materials") or fd.get("materials_shared") or ""
            parts = []
            if topic:
                parts.append(f"Topic: {topic}")
            if materials:
                parts.append(f"Materials: {materials}")
            other = {k:v for k,v in fd.items() if k not in ("topic","materials","materials_shared")}
            if other:
                parts.append("Details: " + ", ".join(f"{k}={v}" for k,v in other.items()))
            summary_text = " | ".join(parts) if parts else "No notes provided."
        else:
            summary_text = "No notes provided."

        # Topics and sentiment
        if inter.form_data and isinstance(inter.form_data, dict) and inter.form_data.get("topic"):
            topics = simple_extract_topics(str(inter.form_data.get("topic")))
        else:
            topics = simple_extract_topics(summary_text)
        sentiment = simple_sentiment(summary_text)

        inter.summary = summary_text
        inter.topics = topics
        inter.sentiment = sentiment
        inter.status = "processed"
        inter.llm_meta = {"mock": True, "timestamp": datetime.utcnow().isoformat()}
        inter.updated_at = datetime.utcnow()
        db.add(inter)
        db.commit()
    finally:
        db.close()

# -------------------------
# Groq-based processor (if key present)
# -------------------------
def process_interaction_with_groq(interaction_id: int):
    db = SessionLocal()
    try:
        inter = db.query(Interaction).filter(Interaction.id == interaction_id).first()
        if not inter:
            return

        if inter.raw_text and inter.raw_text.strip():
            content = inter.raw_text.strip()
            mode = "chat"
        elif inter.form_data and isinstance(inter.form_data, dict):
            fd = inter.form_data
            topic = fd.get("topic") or ""
            materials = fd.get("materials") or fd.get("materials_shared") or ""
            parts = []
            if topic:
                parts.append(f"Topic: {topic}")
            if materials:
                parts.append(f"Materials: {materials}")
            other = {k:v for k,v in fd.items() if k not in ("topic","materials","materials_shared")}
            if other:
                parts.append("Details: " + ", ".join(f"{k}={v}" for k,v in other.items()))
            content = " | ".join(parts) if parts else ""
            mode = "form"
        else:
            content = ""
            mode = "none"

        system_prompt = (
            "You are a concise medical rep assistant. Given a sales rep's notes or form data about "
            "a meeting with an HCP (doctor), produce a JSON object with keys: summary (short human sentence), "
            "topics (array of short keywords), sentiment (one of positive/neutral/negative). "
            "Return ONLY valid JSON. Example: "
            '{"summary":"Met Dr. X about product Y; sent brochure","topics":["diabetes","brochure"],"sentiment":"neutral"}'
        )

        user_prompt = f"Mode: {mode}\n\nContent:\n{content}\n\nReturn only JSON as described."

        try:
            resp = call_groq_chat(system_prompt=system_prompt, user_prompt=user_prompt, model="gemma2-9b-it", temperature=0.0, max_tokens=256)
            text = (resp.get("text") or "").strip()

            # Extract JSON block
            m = re.search(r"\{.*\}", text, flags=re.DOTALL)
            candidate = m.group(0) if m else text

            try:
                parsed = json.loads(candidate)
            except Exception:
                parsed = {"summary": text[:500], "topics": [], "sentiment": "neutral"}

            summary_text = parsed.get("summary") or parsed.get("summary_text") or (text[:500] if text else "No notes provided.")
            topics = parsed.get("topics") or parsed.get("keywords") or []
            sentiment = parsed.get("sentiment") or "neutral"

            inter.summary = summary_text
            inter.topics = topics
            inter.sentiment = sentiment
            inter.status = "processed"
            inter.llm_meta = {"groq_raw": resp.get("raw"), "timestamp": datetime.utcnow().isoformat()}
            inter.updated_at = datetime.utcnow()
            db.add(inter)
            db.commit()
            return
        except Exception as e:
            # fallback to mock if Groq call fails
            print("Groq call failed:", str(e))
            mock_process_interaction(interaction_id)
            return
    finally:
        db.close()

# -------------------------
# Endpoints
# -------------------------
@app.get("/v1/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}


# HCP endpoints
@app.post("/v1/hcps", status_code=201)
def create_hcp(payload: HcpCreate, db: Session = Depends(get_db)):
    h = HCP(
        name=payload.name,
        speciality=payload.speciality,
        organisation=payload.organisation,
        contact=payload.contact,
    )
    db.add(h)
    db.commit()
    db.refresh(h)
    return {"id": h.id, "name": h.name}

@app.get("/v1/hcps")
def list_hcps(db: Session = Depends(get_db)):
    rows = db.query(HCP).order_by(HCP.name).all()
    return [{"id": r.id, "name": r.name, "speciality": r.speciality, "organisation": r.organisation} for r in rows]


# Interaction endpoints
@app.post("/v1/interactions", status_code=201)
def create_interaction(payload: InteractionCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    inter = Interaction(
        hcp_id=payload.hcp_id,
        rep_id=payload.rep_id,
        mode=payload.mode,
        raw_text=payload.raw_text,
        form_data=payload.form_data,
        status="pending"
    )
    db.add(inter)
    db.commit()
    db.refresh(inter)

    # choose processing method
    if USE_REAL_GROQ:
        background_tasks.add_task(process_interaction_with_groq, inter.id)
    else:
        background_tasks.add_task(mock_process_interaction, inter.id)

    return {"id": inter.id, "status": inter.status, "created_at": inter.created_at.isoformat()}

@app.get("/v1/interactions")
def list_interactions(hcp_id: Optional[int] = None, db: Session = Depends(get_db)):
    q = db.query(Interaction)
    if hcp_id:
        q = q.filter(Interaction.hcp_id == hcp_id)
    rows = q.order_by(Interaction.created_at.desc()).limit(200).all()
    return [
        {
            "id": r.id,
            "hcp_id": r.hcp_id,
            "rep_id": r.rep_id,
            "mode": r.mode,
            "summary": r.summary,
            "status": r.status,
            "created_at": r.created_at.isoformat()
        }
        for r in rows
    ]

@app.get("/v1/interactions/{interaction_id}")
def get_interaction(interaction_id: int, db: Session = Depends(get_db)):
    inter = db.query(Interaction).filter(Interaction.id == interaction_id).first()
    if not inter:
        raise HTTPException(status_code=404, detail="Not found")
    return {
        "id": inter.id,
        "hcp_id": inter.hcp_id,
        "rep_id": inter.rep_id,
        "mode": inter.mode,
        "raw_text": inter.raw_text,
        "form_data": inter.form_data,
        "summary": inter.summary,
        "topics": inter.topics,
        "sentiment": inter.sentiment,
        "status": inter.status,
        "created_at": inter.created_at.isoformat(),
        "updated_at": inter.updated_at.isoformat() if inter.updated_at else None,
        "llm_meta": inter.llm_meta
    }

@app.put("/v1/interactions/{interaction_id}")
def edit_interaction(interaction_id: int, payload: InteractionEdit, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    inter = db.query(Interaction).filter(Interaction.id == interaction_id).first()
    if not inter:
        raise HTTPException(status_code=404, detail="Not found")
    for k, v in payload.updates.items():
        if hasattr(inter, k):
            setattr(inter, k, v)
    inter.status = "pending"
    db.add(inter)
    db.commit()

    if USE_REAL_GROQ:
        background_tasks.add_task(process_interaction_with_groq, inter.id)
    else:
        background_tasks.add_task(mock_process_interaction, inter.id)

    return {"id": inter.id, "status": inter.status}

@app.post("/v1/interactions/{interaction_id}/process")
def process_interaction_now(interaction_id: int, db: Session = Depends(get_db)):
    inter = db.query(Interaction).filter(Interaction.id == interaction_id).first()
    if not inter:
        raise HTTPException(status_code=404, detail="Not found")
    if USE_REAL_GROQ:
        process_interaction_with_groq(interaction_id)
    else:
        mock_process_interaction(interaction_id)
    return {"id": interaction_id, "status": "processed"}

# -------------------------
# Tool 4: Generate Follow-ups
# -------------------------
@app.post("/v1/interactions/{interaction_id}/generate_followups")
def generate_followups(interaction_id: int, db: Session = Depends(get_db)):
    inter = db.query(Interaction).filter(Interaction.id == interaction_id).first()
    if not inter:
        raise HTTPException(status_code=404, detail="Not found")

    base_text = (inter.summary or inter.raw_text or (json.dumps(inter.form_data) if inter.form_data else ""))

    followups = []
    if "follow up" in base_text.lower() or "follow-up" in base_text.lower():
        followups.append("Schedule a follow-up call in 7 days")
    followups.extend([
        "Send product brochure",
        "Email clinical data summary",
        "Request consent for sample delivery"
    ])

    # dedupe and limit
    seen = set()
    dedup = []
    for f in followups:
        if f not in seen:
            seen.add(f)
            dedup.append(f)
        if len(dedup) >= 6:
            break

    inter.followups = dedup
    db.add(inter)
    db.commit()

    return {"interaction_id": interaction_id, "followups": dedup}

# -------------------------
# Tool 5: HCP Trend Summary
# -------------------------
@app.post("/v1/hcps/{hcp_id}/trend_summary")
def trend_summary(hcp_id: int, db: Session = Depends(get_db)):
    interactions = (
        db.query(Interaction)
        .filter(Interaction.hcp_id == hcp_id)
        .order_by(Interaction.created_at.desc())
        .limit(20)
        .all()
    )

    if not interactions:
        return {"hcp_id": hcp_id, "trend_summary": "No recent interactions.", "topics": []}

    summaries = []
    for i in interactions:
        if i.summary:
            summaries.append(i.summary)
        elif i.raw_text:
            summaries.append(i.raw_text[:300])
        elif i.form_data:
            summaries.append(json.dumps(i.form_data))

    combined = " ".join(summaries)
    topics = simple_extract_topics(combined, max_topics=8)

    if topics:
        summary_text = f"Recent topics: {', '.join(topics[:6])}."
    else:
        summary_text = "No dominant topics detected in recent interactions."

    return {"hcp_id": hcp_id, "trend_summary": summary_text, "topics": topics}
