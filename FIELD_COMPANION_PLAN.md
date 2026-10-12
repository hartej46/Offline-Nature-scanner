# Field Companion — 3-Day Build Plan (for the AI coding agent)

> **How to use this file:** Give the agent this whole file. Then say: *"Work on Checkpoint N. Do not start N+1 until every box in N is ticked and I confirm."* Paste real error output back to the agent instead of describing it.

## 0. Project in one paragraph

An **offline, voice-first nature companion** for walks. The user talks to it ("what's that bird?") or sends a photo of a plant/insect. Dedicated classifiers propose candidates, **Gemma 4 E4B (open weights, runs locally)** reasons over them with a local species checklist and tells the user *what to look at to confirm*, so their eyes go back to the world, not the screen. Everything is stored locally in a trail journal. No cloud, no account, no per-query cost.

**Challenge theme:** "Touch Grass" (open-weight models, gets people outside; bonus for using it outdoors and reporting honestly).

## 1. Non-negotiable principles

1. **Gemma is the orchestrator, not the classifier.** Birds come from a bird-audio classifier, plants/insects from a vision path. Gemma explains, compares candidates, asks the user to observe a feature, and calls tools.
2. **Grounded answers only.** Every species claim must come from a tool result (classifier output or the local checklist). If confidence is low, Gemma says "not sure" and suggests what to observe or record again.
3. **Offline by default.** After the one-time setup download step, the app must run with Wi-Fi off. Test this explicitly.
4. **Safety guardrail:** for plants and fungi, never say it is safe to eat/touch. Hard-code a disclaimer in the system prompt AND in the UI.
5. **Model-swappable:** the app talks to an OpenAI-compatible endpoint via env vars (`LLM_BASE_URL`, `LLM_MODEL`). Swapping E4B ↔ E2B must need zero code changes.
6. **Keep it small.** Skip anything not in a checkpoint. Cut scope before cutting testing.

## 2. Stack (decided, don't re-debate)

| Layer | Choice |
|---|---|
| LLM runtime (dev, Mac) | **Ollama** (`gemma4:e4b`) first; fall back to **llama.cpp** (`brew install llama.cpp`, Metal) or **mlx-vlm** if Ollama image/audio input misbehaves |
| Backend | Python 3.11+, **FastAPI**, SQLite |
| Frontend | Single mobile-first web page (vanilla JS or small Vite app), big Listen button using file-input capture (see 2.2), installable as PWA, design per section 3b |
| Bird audio | **BirdNET** via `birdnetlib` (verify licence: model weights are non-commercial, fine for this challenge, state it in the README) |
| Plants/insects | Gemma vision as baseline; optional fine-tuned or dedicated classifier only if time allows |
| Species data | Regional checklist from GBIF or eBird/iNaturalist open data, downloaded once into SQLite |
| Speech out | Piper TTS (open source, local) or macOS `say` as the fallback |
| Speech in | Try Gemma native audio (30 s max) first; fallback **whisper.cpp** |

Config lives in `.env`: `LLM_BASE_URL`, `LLM_MODEL`, `REGION_BBOX`, `DB_PATH`.

## 3. Repo layout

```
field-companion/
  app/
    main.py            # FastAPI routes
    llm.py             # OpenAI-compatible client wrapper
    tools.py           # species_lookup, checklist_check, journal_add, journal_search
    agent.py           # tool-calling loop + system prompt
    audio.py           # BirdNET wrapper + audio preprocessing
    vision.py          # image handling
    db.py              # SQLite schema + helpers
  web/                 # frontend
  scripts/
    fetch_checklist.py # one-time online download of regional species data
    eval_run.py        # runs the eval set, prints accuracy + latency
  eval/                # ~50 labelled clips/photos + labels.csv
  README.md
  .env.example
```

---

## 3b. Design tokens and screens (match exactly)

The visual designs are exported from Google Stitch (field-notebook look, not an "AI app" look). **Match the exported designs exactly.** If a detail is missing, use these tokens. Never add chat bubbles, sparkle/robot icons, gradients, shadows, purple or emojis.

| Token | Value |
|---|---|
| Background (paper) | `#F5F1E8` |
| Text (ink) | `#1C1C1A` |
| Accent (moss) | `#4F6B3A` |
| Dividers | 1px hairline, no shadows, no heavy rounded cards |
| Headings / species names | Serif (Newsreader or Source Serif) |
| UI text | Clean sans |
| Scientific names / metadata | Monospace, small caps |
| Icons | Line icons, 1.5px stroke |
| Tap targets | At least 48px, primary actions in the thumb zone |

Screens (390px wide): **Home** (large Listen button, smaller Photograph button, Offline status dot), **Listening** (pulsing ring, hairline waveform, Stop), **Result** (species name, scientific name, confidence label and bar, "Look for" box, other possibilities, Save, "Not right?", plant safety footnote), **Journal** (diary-style list with search), **Species detail** (description, where/when seen, user notes), **Settings** (offline model status, region, privacy note "Everything stays on this phone").

Copy tone: short, plain, no exclamation marks, no emojis; empty states nudge the user outside.

Fonts must be bundled locally, not loaded from a CDN, because the app must work offline (Checkpoint 3.1).

---

## DAY 1 — The brain works (text + photo, grounded)

### Checkpoint 1.1 — Local Gemma running on the Mac
- [ ] Install Ollama, run `ollama pull gemma4:e4b`, then `ollama run gemma4:e4b "hello"`
- [ ] Confirm the OpenAI-compatible endpoint works: `curl localhost:11434/v1/chat/completions` with a test message
- [ ] Send one image to the model (CLI or API) and confirm it describes it
- [ ] Record tokens/sec and RAM use in `NOTES.md`
- **Done when:** a Python script calls the endpoint via the `openai` client and prints a reply.
- **If it fails:** try `llama-server -hf ggml-org/gemma-4-E4B-it-GGUF:Q4_K_M` (port 8080) and switch `LLM_BASE_URL`.

### Checkpoint 1.2 — Project skeleton + DB
- [ ] Create the repo layout above, `.env.example`, `requirements.txt`
- [ ] `db.py` with tables: `species(id, common_name, sci_name, group, region_flag, notes)`, `observations(id, ts, lat, lon, species_id, confidence, source, notes)`
- [ ] `scripts/fetch_checklist.py` downloads a regional list (parameterised by `REGION_BBOX`) into `species`
- **Done when:** `python scripts/fetch_checklist.py` populates the DB, and a query returns at least 100 species.

### Checkpoint 1.3 — Tools + tool-calling loop
- [ ] `tools.py`: `species_lookup(name)`, `checklist_check(name, month)`, `journal_add(...)`, `journal_search(query)`
- [ ] `agent.py`: tool-calling loop with a max of 4 iterations, returns final text plus the list of tools used
- [ ] System prompt rules: be concise (voice output), cite which tool result supports each claim, say "not sure" under the confidence threshold, always end with **one thing to look at or listen for** in the real world, apply the safety rule for plants/fungi
- **Done when:** a text query like "I saw a small black bird with a white wing patch" returns candidates from the checklist, with a confirm-by-looking tip, and never invents a species absent from the DB.

### Checkpoint 1.4 — Photo path
- [ ] `/identify/photo` endpoint: resize the image (long edge ≤ 1024 px), send it to Gemma with the checklist as context
- [ ] The response lists the top 3 candidates, each with a "look for X to confirm" feature
- **Done when:** 10 test plant/insect photos from your own phone produce sensible, hedged answers. Log the failures in `NOTES.md`.

**Day 1 gate:** the text and photo flows work in the terminal and via `curl`, and are grounded in the DB.

---

## DAY 2 — Ears, voice, and the UI

### Checkpoint 2.1 — Bird audio
- [ ] Install `birdnetlib` and confirm it runs on Apple Silicon (TensorFlow can be fiddly; if it blocks you for more than 45 minutes, note it and switch to the fallback below)
- [ ] `audio.py`: take a ≤30 s recording, run BirdNET with the location and week, return the top 5 detections with confidence
- [ ] `/identify/audio` endpoint: BirdNET results go to the agent as tool output; Gemma explains and cross-checks against the checklist (flag any bird not expected in the region or season)
- [ ] **Fallback if BirdNET won't install:** pass the clip to Gemma's native audio input and clearly label results as "lower confidence"
- **Done when:** 10 known recordings (download from Xeno-canto, check each licence) return the correct species in the top 3 for most clips. Record the real hit rate.

### Checkpoint 2.2 — Voice in, voice out
- [ ] **Phone mic constraint:** mobile browsers only allow live mic/camera (`getUserMedia`) on HTTPS or localhost. The phone will reach the Mac over plain `http://<ip>:8000`, so live recording will silently fail there. Do NOT build live in-browser recording first.
- [ ] Build capture with file inputs: `<input type="file" accept="audio/*" capture>` for recordings and `<input type="file" accept="image/*" capture>` for photos. These open the phone's own recorder/camera and work over plain http. Post the resulting file to the backend
- [ ] Optional upgrade only if time remains: local HTTPS via `mkcert` (install its root certificate on the phone) to enable live push-to-talk
- [ ] Speech to text: try Gemma audio first, else whisper.cpp
- [ ] Reply is spoken via Piper (or `say`); keep spoken replies under about 25 words, with the full text on screen
- **Done when:** you can ask a question aloud and hear a grounded answer with no keyboard.

### Checkpoint 2.3 — Mobile-first UI
- [ ] Implement the screens and tokens from section 3b (Home, Listening, Result, Journal, Species detail, Settings) with a big Listen button and a Photograph button
- [ ] Light paper theme, high contrast, readable in sunlight; no clutter
- [ ] Show a **confidence badge** and a **"what to look for"** card for every answer
- [ ] Journal list with species, time, and notes, searchable
- **Done when:** the page is usable one-handed on a phone viewport.

### Checkpoint 2.4 — Eval harness
- [ ] `eval/` with ~50 items (audio + photos + text questions) and `labels.csv`
- [ ] `scripts/eval_run.py` prints top-1/top-3 accuracy, "not sure" rate, hallucination count (species named that aren't in tool output), and median latency
- **Done when:** one command produces a results table you can paste into the write-up.

**Day 2 gate:** voice, audio and photo flows work end to end on the Mac, and the eval table exists.

---

## DAY 3 — Harden, deploy, go outside, write it up

### Checkpoint 3.1 — Offline proof + hardening
- [ ] Turn Wi-Fi off and run the whole flow. Fix anything that tries to reach the internet (fonts, CDN scripts, model downloads)
- [ ] Add timeouts, error messages the user can understand, and a "model still loading" state
- [ ] Log nothing sensitive; GPS and recordings stay in local SQLite and files only
- [ ] Add a `make run` (or `./run.sh`) that starts the LLM server, backend and frontend in one command
- **Done when:** a fresh clone plus the README steps works on a clean machine setup.

### Checkpoint 3.2 — Phone access (pick the path in section 5)
- [ ] Path A (core): laptop runs everything, the phone is the client over a local network
  - Run the backend with `uvicorn app.main:app --host 0.0.0.0 --port 8000` (the LLM server stays on localhost)
  - Find the Mac address with `ipconfig getifaddr en0`, then open `http://<ip>:8000` on the phone
  - Allow incoming connections if the macOS firewall prompts
  - Test with the phone's hotspot and mobile data OFF to confirm it works with no internet
  - Confirm photo and audio capture work on the phone (file inputs with `capture`)
- [ ] Path B (demo of on-device): Gemma E2B/E4B running natively on the phone via Google's AI Edge Gallery
- **Done when:** you have used the app from your phone away from your home Wi-Fi.

### Checkpoint 3.3 — The real walk (bonus points)
- [ ] 45-60 minutes outside, phone in hand, laptop in a bag if using Path A
- [ ] Log every query: what you asked, the answer, was it right (you confirm by looking), latency, battery
- [ ] Take photos and a short video of using it
- [ ] Write down at least 3 honest failures
- **Done when:** `FIELD_LOG.md` has real data from the walk.

### Checkpoint 3.4 — README + post
- [ ] README: what it is, architecture diagram, setup, how to swap models, known limits, licences (Gemma terms, BirdNET non-commercial, data sources)
- [ ] Post sections: the problem, why open weights mattered (offline, private, swappable, free), what worked better than a closed approach, what didn't, numbers from the eval and the walk
- [ ] Demo video under 90 s, ending outside, not on the screen
- **Done when:** the repo is public and the post draft is ready.

---

## 4. Cut list if you fall behind (cut in this order)

1. Fine-tuning anything
2. Piper TTS (use `say`)
3. PWA install polish
4. Path B phone demo
5. Vision beyond Gemma baseline

**Never cut:** grounding, the offline test, the eval table, the real walk.

## 5. Risks to watch

- **Gemma audio** is limited to short clips; do not feed it long recordings.
- **BirdNET on Apple Silicon** may need a separate environment; timebox it.
- **Hallucinated species**: check every answer against tool output in the eval.
- **Licences:** check Gemma's terms, BirdNET's weights licence, and each audio/photo source.
- **Heat and battery** outdoors: note it honestly.

## 6. Agent working rules

- Work on one checkpoint at a time; list what you changed and how I can verify it.
- Never fake results; if something fails, show the real error and propose two fixes.
- Prefer boring, well-known libraries.
- Ask me before adding any dependency that isn't in the stack table.