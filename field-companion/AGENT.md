# AGENT RUNTIME & ARCHITECTURE GUIDELINES

> **Mandatory Agent Rule:** Before planning, proposing, or writing any code, the agent **MUST** read [PROGRESS.md](file:///Users/hartej/Hartej46/Hactober/Week1/PROGRESS.md) and [FIELD_COMPANION_PLAN.md](file:///Users/hartej/Hartej46/Hactober/Week1/FIELD_COMPANION_PLAN.md) to understand current checkpoint status, non-negotiable principles, and active constraints.

---

## 1. High-Level System Overview
- **Project**: Field Companion 🌿 (Touch Grass Edition)
- **Concept**: An offline, voice-first nature companion for outdoor walks. Dedicated audio/vision classifiers propose candidates, and local **Gemma 4 E4B** orchestrates tool calls, grounds species against a regional SQLite checklist, and tells the user *what specific physical feature to look at or listen for to confirm in the real world*.
- **Primary Tech Stack**:
  - **Backend**: Python 3.11+, FastAPI, SQLite (WAL mode), Whisper (offline STT), macOS `say` (16-bit PCM WAV TTS), BirdNET / acoustic fallback.
  - **Frontend (Web)**: React 18, TypeScript, Vite, Vanilla CSS design tokens (field-notebook aesthetic, PWA).
  - **Frontend (Mobile)**: React Native CLI (bare workflow, iOS & Android).
  - **LLM Runtime**: Ollama (`gemma4:e4b`) on `http://localhost:11434/v1` (OpenAI-compatible endpoint), swappable to `llama.cpp` or `mlx-vlm`.
- **Primary Objectives**: 100% offline-ready, zero hallucination of ungrounded species, under 25-word voice responses, strict plant/fungi safety, and hands-free outdoor exploration.

---

## 2. Core Operational Tooling & Commands

Always run commands in the respective workspace directories (`field-companion/backend/`, `field-companion/webapp/`, `field-companion/mobile/`).

### Quick Start (All Services)
- Run complete system: `./run.sh` from `field-companion/` (starts Ollama, FastAPI backend on port 8000, Vite webapp on port 5173).

### Backend (`field-companion/backend/`)
- **Run dev server**: `python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`
- **Populate regional checklist**: `python3 scripts/fetch_checklist.py`
- **Run eval harness**: `python3 scripts/eval_run.py [num_samples]`
- **Run audio benchmark**: `python3 scripts/test_audio.py`
- **Run agent verification test**: `python3 scripts/test_agent.py`

### Web Frontend (`field-companion/webapp/`)
- **Install dependencies**: `npm install`
- **Run dev server**: `npm run dev -- --host 0.0.0.0`
- **Production build & typecheck**: `npm run build` (runs `tsc -b && vite build`)

### Mobile App (`field-companion/mobile/`)
- **Install dependencies**: `npm install`
- **Typecheck validation**: `./node_modules/.bin/tsc --noEmit`
- **Start Metro bundler**: `npx react-native start`

---

## 3. Strict Code Conventions & Quality Standards

### Non-Negotiable Core Principles (from `FIELD_COMPANION_PLAN.md`)
1. **Gemma is the Orchestrator, Not the Classifier**:
   - Birds come from the audio path, plants/insects from vision/description.
   - Gemma compares candidates, calls tools (`species_lookup`, `checklist_check`), and formulates observation tips.
2. **Grounded Answers Only**:
   - Every species claim MUST come from a tool result or local checklist query.
   - If confidence is low or unverified, Gemma MUST say *"not sure"* and suggest what to observe or record again. Never invent species names absent from the SQLite database.
3. **Safety Guardrail (Critical)**:
   - For plants and fungi, **NEVER** state that anything is safe to touch, eat, taste, or ingest.
   - Hard-code the disclaimer in the system prompt AND the UI:
     `"Do not eat or touch any plant or fungus based on this identification."`
4. **Offline by Default**:
   - Zero cloud dependencies at runtime. Fonts must be bundled locally (never loaded from external CDNs).
   - Audio transcription (Whisper) and speech synthesis (macOS `say`) must operate without network access.
5. **Model-Swappable via Env Vars**:
   - All LLM interactions must route through OpenAI-compatible client configured via `LLM_BASE_URL` and `LLM_MODEL`.
   - Swapping models (e.g. `gemma4:e4b` ↔ `gemma4:2b`) must require zero code changes.

### Design & Aesthetics (Section 3b)
- **Field-Notebook Aesthetic**:
  - Background (Paper): `#F5F1E8`
  - Text (Ink): `#1C1C1A`
  - Accent (Moss): `#4F6B3A`
  - Dividers: 1px hairline, no heavy rounded cards, no box shadows.
  - Headings: Serif (`Newsreader` or `Source Serif`).
  - UI text: Clean sans.
  - Scientific names / metadata: Monospace, small caps.
  - Line icons: 1.5px stroke.
- **Forbidden UI Elements**:
  - ❌ NEVER add chat bubbles, sparkle icons, robot avatars, gradients, heavy shadows, purple accents, or emojis.
- **Copy Tone**:
  - Short, plain, understated. No exclamation marks, no cheerful assistant pleasantries.
  - Spoken voice replies must be **under 25 words**; full details remain on screen.
  - Always end with **one specific real-world feature to look at or listen for** (eyes go back to nature).

---

## 4. Architectural Boundaries (Do's & Don'ts)

### ⛔ Hard Guardrails (Forbidden Actions)
1. **Never skip ahead across checkpoints**: Work checkpoint-by-checkpoint. Complete and verify Checkpoint N before beginning N+1.
2. **Never hallucinate species**: If a species is not verified via `species_lookup` in SQLite, it must not be declared as the identified organism.
3. **Never omit the plant/fungi safety warning**: Every photo result, species card, and prompt must maintain the safety footnote.
4. **Never rely on external CDNs or cloud APIs**: No Google Fonts CDN links, no cloud vision APIs, no external Whisper/TTS cloud endpoints.
5. **Never break plain HTTP mobile capture**: Mobile browsers restrict live `getUserMedia` mic over plain HTTP LAN. Keep `<input type="file" accept="audio/*" capture>` and `<input type="file" accept="image/*" capture>` as primary inputs.

### ✅ Mandatory Workflows
- **Check Progress First**: Always read `PROGRESS.md` at the start of every session to align on the current task and past checkpoints.
- **Update Tracking Files**: Whenever completing a checkpoint, update both `PROGRESS.md` (checklist & work log) and `NOTES.md` (metrics & benchmark tables).
- **Enforce Build Verification**: Before ending any code edit, verify that `npm run build` (webapp) and `tsc --noEmit` (mobile) pass with zero errors.

---

## 5. Agent Verification Checklist Before Proposing Changes

Before marking any checkpoint complete or proposing code changes, verify:
- [ ] Read `PROGRESS.md` and confirmed active checkpoint goals.
- [ ] Answers remain grounded in SQLite checklist (`data/field_companion.db`).
- [ ] Plant/fungi safety disclaimer is intact in both system prompts and UI components.
- [ ] Spoken replies are constrained to <= 25 words (`condense_for_speech`).
- [ ] Field-notebook design tokens applied (paper `#F5F1E8`, ink `#1C1C1A`, moss `#4F6B3A`, hairline borders, zero emojis).
- [ ] Webapp compiles cleanly: `npm run build` in `field-companion/webapp/`.
- [ ] Mobile compiles cleanly: `./node_modules/.bin/tsc --noEmit` in `field-companion/mobile/`.
- [ ] Backend routes and test scripts pass cleanly: `python3 scripts/test_audio.py` / `python3 scripts/eval_run.py`.
- [ ] Updated `PROGRESS.md` status checklist and work log table.
