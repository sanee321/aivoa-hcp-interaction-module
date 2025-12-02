AIVOA – HCP Interaction Module (Task-1 Assignment)

This repository contains a full implementation of the HCP Interaction Module for the AIVOA AI-first CRM system.
The solution includes:

Backend (FastAPI + PostgreSQL + SQLAlchemy)

Frontend (React + Redux Toolkit)

Deterministic AI workflow

Optional Groq LLM integration

Complete pipeline for HCP roster, interaction logging, and AI processing

This project fulfills 100% requirements of the Task-1 assignment.

⭐ Features
✔ HCP Roster Management

Add HCPs (Doctor profiles)

List existing HCPs

Linked interactions for each HCP

✔ Interaction Logging

Supports two modes:

Structured Form

Unstructured Chat / Free-text

✔ AI-Plugged Processing Tools

Each interaction supports 5 independent tools:

Summarization

Topic Extraction

Sentiment Classification

Follow-up Suggestions

Trend Summary (HCP-level)

Processing is routed via:

Groq LLM (if API key present)

OR Deterministic Mock Engine (if no API key)

✔ Frontend UI

HCP dropdown

Interaction creation screen

Processed output viewer

Buttons for:

Generate Follow-ups

Generate Trend Summary

📁 Project Structure
aivoa-hcp-interaction-module/
│
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md  (backend-specific)
│
├── frontend/
│   ├── package.json
│   ├── public/
│   └── src/
│       ├── api/apiClient.js
│       ├── app/store.js
│       ├── features/interactions/
│       │     ├── interactionsSlice.js
│       │     └── LogInteractionScreen.jsx
│       ├── App.jsx
│       └── index.js
│
└── README.md   (this file)

⚙ Backend Setup
1. Install Dependencies
cd backend
pip install -r requirements.txt

2. Create .env

Use the sample file:

📌 backend/.env.example

DATABASE_URL=postgresql://crm_user:YourPassword@localhost:5433/crm_ai
GROQ_API_KEY=your_groq_api_key_optional


Rename to .env:

cp .env.example .env

3. Run Backend
python -m uvicorn main:app --reload --port 8000


Backend opens at:

API Docs: http://localhost:8000/docs

Health Check: http://localhost:8000/v1/health

💻 Frontend Setup
cd frontend
npm install
npm start


Frontend runs at:

👉 http://localhost:3000

Make sure backend is running at port 8000.

🧠 AI Engine (LLM or Mock)
If GROQ_API_KEY is provided:

Real LLM responses from Groq via llama3-8b-8192

If no API key:

Automatically uses deterministic mock engine

Produces consistent outputs required for evaluation:

Summary

Topics

Sentiment

Follow-ups

Trend Summary

No dependency on external tools ensures the assignment can be evaluated cleanly.

🔥 API Endpoints (Key)
HCP
Method	Endpoint	Description
GET	/v1/hcps	List HCPs
POST	/v1/hcps	Create HCP
Interactions
Method	Endpoint	Description
POST	/v1/interactions	Log interaction
GET	/v1/interactions	List interactions
POST	/v1/interactions/{id}/process	Process interaction
Tools
Method	Endpoint	Description
POST	/v1/interactions/{id}/generate_followups	Generate follow-ups
POST	/v1/hcps/{id}/trend_summary	Generate trend summary
🎥 Demo Flow (for video submission)

Start PostgreSQL

Run FastAPI backend

Open /docs → show available endpoints

Create an HCP

Start React frontend

Select HCP from dropdown

Log interaction (form or chat)

Show auto-processed summary/topics/sentiment

Click Generate Follow-Ups

Click Trend Summary

Show pgAdmin tables (interaction + hcp)

End

📌 License

This project is created exclusively as part of the AIVOA Task-1 Selection Assignment
