# Field Companion 🌿
*An offline, voice-first nature companion for outdoor walks*

**Challenge Theme:** "Touch Grass" — Open-weight AI models that get people outside.

---

## 1. Overview

Field Companion is an offline-first nature companion designed for outdoor exploration. When you walk through a forest, meadow, or park, you talk to it or capture photos of unfamiliar plants and birds.

Rather than acting as an opaque chatbot, **Gemma 4 E4B acts as an orchestrator**:
1. Dedicated classifiers or user descriptions propose species candidates.
2. Gemma grounds each candidate against a **local SQLite regional species checklist** (730+ species).
3. The companion tells you **what specific physical feature to look at or listen for to confirm** — so your eyes return to the real world, not stuck on your screen.
4. Every confirmed sighting is saved to a local, private **Trail Journal**.
5. **Zero cloud connection**, zero per-query cost, and 100% private.

---

## 2. Architecture

```
┌────────────────────────────────────────────────────────┐
│                   FIELD COMPANION                      │
│                                                        │
│  [ React Web App (PWA) ]    [ React Native Mobile ]    │
│  Paper UI, Listen/Photo     Bare CLI, iOS & Android    │
└───────────────┬────────────────────────┬───────────────┘
                │                        │
                ▼                        ▼
┌────────────────────────────────────────────────────────┐
│               FastAPI Backend (Python)                 │
│  /identify/text   /identify/photo   /identify/audio   │
│  /journal         /species          /status           │
└───────────────┬────────────────────────┬───────────────┘
                │                        │
        ┌───────┴───────┐        ┌───────┴───────┐
        ▼               ▼        ▼               ▼
┌──────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│  Ollama LLM  │ │   SQLite    │ │  BirdNET    │ │ Pillow/Ops  │
│  gemma4:e4b  │ │  Checklist  │ │ Audio Dete- │ │ Max 1024px  │
│ (OpenAI API) │ │ & Journal   │ │    ctions   │ │ Resizing    │
└──────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

---

## 3. Tech Stack

- **LLM Runtime:** Ollama running `gemma4:e4b` locally via OpenAI-compatible endpoints (`/v1/chat/completions`). Model-swappable via `LLM_BASE_URL` and `LLM_MODEL`.
- **Backend API:** Python 3.11+, FastAPI, Uvicorn, SQLite (WAL mode).
- **Web App:** React 18, TypeScript, Vite. Mobile-first design matching field-notebook aesthetic (paper background `#F5F1E8`, ink `#1C1C1A`, moss accent `#4F6B3A`).
- **Mobile App:** React Native CLI (bare workflow).
- **Species Data:** Regional checklist from GBIF open data loaded into local SQLite database.

---

## 4. Setup & Running

### Prerequisites
1. [Ollama](https://ollama.com) installed with Gemma 4:
   ```bash
   ollama pull gemma4:e4b
   ```
2. Python 3.11+ and Node.js 18+

### Quick Start (One Command)
Run everything with the included runner script:
```bash
./run.sh
```
This automatically starts:
- Ollama runtime on `http://localhost:11434`
- FastAPI backend on `http://localhost:8000`
- React web app on `http://localhost:5173`

### Manual Setup

#### Backend
```bash
cd backend
cp .env.example .env
pip install -r requirements.txt
python scripts/fetch_checklist.py   # Populates regional checklist from GBIF
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### Web App
```bash
cd webapp
npm install
npm run dev
```

#### Mobile App (React Native)
```bash
cd mobile
npm install
npx react-native start
```

---

## 5. Non-Negotiable Principles & Guardrails

1. **Grounded Answers Only:** Every claimed species must be verified by `species_lookup` or `checklist_check`. If confidence is low, Gemma says "not sure" and asks what to observe.
2. **Plant & Fungi Safety:** Hard-coded disclaimers in the system prompt and UI: *"Do not eat or touch any plant or fungus based on this identification."*
3. **Eyes on Nature:** Every identification concludes with one specific field marker to observe (e.g. *"Look for white outer tail feathers when perched"*).
4. **100% Offline & Private:** No location data, audio clips, or photos leave your local hardware.

---

## 6. Model Swapping

Swapping models requires zero code changes. Update `.env`:
```env
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=gemma4:e4b
```
Or switch to llama.cpp / mlx-vlm:
```env
LLM_BASE_URL=http://localhost:8080/v1
LLM_MODEL=gemma-4-E4B-it
```

---

## 7. Licences & Acknowledgements

- **Gemma 4:** Subject to Google Gemma Terms of Use.
- **BirdNET:** Model weights non-commercial research licence.
- **Species Occurrence Data:** GBIF (Global Biodiversity Information Facility) Open Data.
