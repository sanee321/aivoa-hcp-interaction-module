# backend/langgraph_client.py
import os
import requests
from typing import Dict, Any, Optional

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")  # put your Groq API key in .env

def call_groq_chat(system_prompt: str, user_prompt: str, model: str = "gemma2-9b-it", max_tokens: int = 512, temperature: float = 0.0) -> Dict[str, Any]:
    """
    Call Groq chat completion endpoint and return parsed text output.
    If GROQ_API_KEY is not set, raises ValueError.
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

    # Groq returns a structure similar to OpenAI; adapt if necessary
    # Grab the top assistant message text
    # Some Groq responses put text under data['choices'][0]['message']['content']
    text = ""
    try:
        choices = data.get("choices", [])
        if choices:
            # handle both shape variants
            msg = choices[0].get("message") or choices[0].get("delta") or choices[0]
            if isinstance(msg, dict):
                text = msg.get("content") or msg.get("text") or ""
            else:
                text = str(msg)
    except Exception:
        text = ""

    return {"raw": data, "text": text}
