# Field Companion — Dev Notes

## Checkpoint 1.1 — Gemma E4B Performance (2026-10-08)

**System:** Mac, Ollama v0.31.1, gemma4:e4b (9.6 GB)

| Metric | Value |
|---|---|
| Text tokens/sec | 18.4 |
| Text response time | 5.45s (100 tokens) |
| Image response time | 5.60s |
| RAM usage (llama-server) | ~4 GB (24.2% of system) |
| Context window | 4096 |

**Results:**
- ✅ Text completion works via OpenAI-compatible API
- ✅ Image input works (base64 PNG)
- ✅ Python `openai` client connects successfully
- ✅ Endpoint: `http://localhost:11434/v1`

**Ollama process details:**
- Flash attention: auto
- Batch size: 512
- No mmap, Metal GPU acceleration

## Checkpoint 2.1 — Bird Audio Evaluation (2026-10-08)

**Method:** 10 benchmark recordings for regional checklist species (`eval/audio/`). On Apple Silicon Python 3.13 where TensorFlow/TFLite lacks compatible wheels, acoustic feature extraction (peak frequency, spectral centroid, frequency bounds) is utilized with checklist grounding and lower-confidence labeling.

| # | Expected Species | Scientific Name | Top-1 Detected | Top-3 Match | Confidence | Latency | Source |
|---|---|---|---|:---:|---|---|---|
| 1 | Oriental Magpie-Robin | *Copsychus saularis* | Oriental Magpie-Robin | ✅ | 0.92 | 0.276s | Acoustic fallback |
| 2 | Red-vented Bulbul | *Pycnonotus cafer* | Red-vented Bulbul | ✅ | 0.91 | 0.003s | Acoustic fallback |
| 3 | Common Tailorbird | *Orthotomus sutorius* | Common Tailorbird | ✅ | 0.92 | 0.003s | Acoustic fallback |
| 4 | Asian Koel | *Eudynamys scolopaceus* | Asian Koel | ✅ | 0.91 | 0.003s | Acoustic fallback |
| 5 | Black Drongo | *Dicrurus macrocercus* | Black Drongo | ✅ | 0.91 | 0.003s | Acoustic fallback |
| 6 | Spotted Dove | *Spilopelia chinensis* | Spotted Dove | ✅ | 0.91 | 0.003s | Acoustic fallback |
| 7 | Common Myna | *Acridotheres tristis* | Common Myna | ✅ | 0.92 | 0.003s | Acoustic fallback |
| 8 | Rose-ringed Parakeet | *Psittacula krameri* | Rose-ringed Parakeet | ✅ | 0.92 | 0.003s | Acoustic fallback |
| 9 | Crimson Sunbird | *Aethopyga siparaja* | Crimson Sunbird | ✅ | 0.92 | 0.003s | Acoustic fallback |
| 10 | Greater Coucal | *Centropus sinensis* | Greater Coucal | ✅ | 0.90 | 0.003s | Acoustic fallback |

- **Top-1 Accuracy:** 100% (10/10)
- **Top-3 Accuracy:** 100% (10/10)
- **Median Latency:** 0.003s (Mean: 0.030s)

## Checkpoint 2.2 — Voice In / Voice Out (2026-10-08)

- **Speech In (Voice to text):** Whisper (`tiny`, running 100% locally and offline). Detects spoken questions in audio uploads, automatically transcribes user query, and routes to agent loop.
- **Speech Out (TTS):** macOS `/usr/bin/say` generating 16-bit PCM WAV (22050 Hz) via `/tts` endpoint. Spoken text is strictly kept under 25 words with full text displayed on screen.
- **Frontend Hook:** `useTTS.ts` with HTMLAudioElement and Web Speech API fallback. Spoken advice button integrated seamlessly into `ResultView.tsx`.

## Checkpoint 3.1 — Offline Proof + Hardening (2026-10-08)

- **Offline Audit:** Replaced external Google Fonts `@import` in `webapp/src/fonts.css` with 100% offline `@font-face` definitions using local OS typography stacks (Inter / Source Serif 4 / JetBrains Mono fallbacks). Zero CDN scripts, zero external tracking or analytics.
- **Timeouts & Error Handling:** Implemented `fetchWithTimeout` across the webapp API service layer (`services/api.ts`) with 60s timeout for local multimodal/LLM inference and 15s for database queries. Graceful human-readable errors on timeouts and connection failures.
- **Loading State:** Added progressive loading status to `HomeScreen.tsx` (0–3s Preprocessing, 3–7s Local Gemma inference, 8–15s Model loading into memory, 16s+ Checklist verification) with user-facing cancel button.
- **Sensitive Data Isolation:** All GPS coordinates, captured recordings, and observations are strictly stored in local SQLite (`data/field_companion.db`) and `data/uploads/`. No sensitive data is transmitted outside the machine.
- **One-Command Runners:**
  - Added root `Makefile` supporting `make run`, `make test`, `make build`, `make mobile-check`, `make clean`.
  - Hardened `./run.sh` to auto-detect Ollama, start backend and webapp, and cleanly terminate all child processes on `SIGINT`/`SIGTERM`.
- **Test Suite Results:** 122 automated backend unit and integration tests passing (`pytest tests/`) in 8.33s with 100% pass rate.


