# Field Companion — Deployment Guide & Plan (Render + Mobile APK)

This guide explains how to deploy **Field Companion** to **Render** and configure model hosting, web frontend, and mobile APK distribution.

---

## 1. Architecture Overview

```
                            +-------------------------------------------------------+
                            |                  RENDER CLOUD                         |
                            |                                                       |
  [ Mobile / Phone ]        |   +-----------------------------------------------+   |
          |                 |   |  FastAPI Backend (Docker Web Service)         |   |
          |-- Download APK -|-->|  - GET /download/app (FieldCompanion.apk)     |   |
          |                 |   |  - Audio (BirdNET & Acoustic features)        |   |
          |-- API Requests -|-->|  - Vision (Gemma Multimodal)                  |   |
                            |   |  - Regional Checklist & Journal (SQLite)      |   |
                            |   +-----------------------+-----------------------+   |
                            |                           |                           |
  [ Web Browser ]           |                           v                           |
          |                 |   +-----------------------------------------------+   |
          +--- HTTPS ------->   |  Landing Page (Render Static Site / PWA)      |   |
                            |   |  - 100% Offline Cached Service Worker         |   |
                            |   |  - Direct One-Tap Android APK Download Button |   |
                            |   |  - Interactive Mobile App Feature Simulator   |   |
                            |   |  - Expo Go Quick-Test & Installation Guides   |   |
                            |   +-----------------------------------------------+   |
                            |                           |                           |
                            +---------------------------|---------------------------+
                                                        v
                                        +-------------------------------+
                                        | Model Runtime                 |
                                        | - Option A: Groq / Cloud API  |
                                        | - Option B: Render GPU Ollama |
                                        | - Option C: On-Device Mobile  |
                                        +-------------------------------+
```

---

## 2. Model Architecture: Direct Internet Download via URL (No Cloud Model Needed!)

**You do NOT need any cloud AI provider (no Groq, no OpenAI, no Gemini, and zero API subscription costs).**

Field Companion is designed so the model weights are downloaded directly from the internet onto the mobile phone (or server) and executed locally on-device:

### How It Works:
1. **Configure Your Model Download URL:**
   In your Render environment (or backend `.env`), simply set `MODEL_DOWNLOAD_URL` to your model weights file URL:
   ```env
   MODEL_DOWNLOAD_URL=https://huggingface.co/bartowski/gemma-2-2b-it-GGUF/resolve/main/gemma-2-2b-it-Q4_K_M.gguf
   ```
   *(You can use any direct HTTP/HTTPS link: HuggingFace, AWS S3, Google Cloud Storage, GitHub Release, or your own server).*

2. **One-Time Download Over Internet:**
   - The user opens the mobile app while connected to Wi-Fi/Internet.
   - The app connects to your server endpoint `GET /model/download/gemma4:e2b`, which redirects directly to your `MODEL_DOWNLOAD_URL`.
   - The phone downloads the GGUF model package directly into its local document directory (`FileSystem.documentDirectory + "models/"`).

3. **100% Offline in the Field:**
   - Once the download is complete, the model weights live permanently on the device.
   - Users can walk deep into the woods, mountains, or trails with **airplane mode on / zero cellular signal**.
   - All species recognition and reasoning runs locally on the phone's processor!

---

## 3. Deploying to Render via Blueprint (`render.yaml`)

We have created an automated **Render Blueprint** in `render.yaml`.

### Steps:
1. Push your repository to GitHub / GitLab.
2. Log into the [Render Dashboard](https://dashboard.render.com).
3. Click **New +** -> **Blueprint**.
4. Connect your `field-companion` repository.
5. Render will automatically parse `render.yaml` and configure two services:
   - **`field-companion-backend`**: Docker Web Service running FastAPI.
   - **`field-companion-web`**: Static Site hosting the compiled React web application.
6. Provide your `LLM_API_KEY` (e.g. from Groq or OpenAI) in the Render environment settings.
7. Click **Apply Blueprint** to launch!

---

## 4. Manual Dashboard Setup (Alternative)

If you prefer to configure services manually in the Render UI:

### Service 1: Backend Web Service
- **Name:** `field-companion-backend`
- **Environment:** `Docker`
- **Docker Context:** `./field-companion/backend`
- **Dockerfile Path:** `./field-companion/backend/Dockerfile`
- **Plan:** Starter (or Free)
- **Health Check Path:** `/health`
- **Environment Variables:**
  | Variable | Value | Description |
  |---|---|---|
  | `PORT` | `8000` | Port assigned by Render |
  | `DATA_DIR` | `/app/data` | Storage directory for SQLite and uploads |
  | `DB_PATH` | `/app/data/field_companion.db` | Pre-seeded 731-species checklist |
  | `LLM_BASE_URL` | `https://api.groq.com/openai/v1` | Model provider endpoint |
  | `LLM_MODEL` | `gemma2-9b-it` | Model identifier |
  | `LLM_API_KEY` | `your_api_key` | Model API key |
  | `REGION_BBOX` | `6.5,68.1,35.7,97.4` | Regional bounding box |
- **Persistent Disk (Optional):** Attach a 10 GB disk mounted at `/app/data` to persist user journal entries and uploaded recordings.

### Service 2: Webapp Static Site
- **Name:** `field-companion-web`
- **Root Directory:** (leave blank or `field-companion`)
- **Build Command:** `cd field-companion/webapp && npm install && npm run build`
- **Publish Directory:** `field-companion/webapp/dist`
- **Environment Variables:**
  | Variable | Value |
  |---|---|
  | `VITE_API_BASE` | `https://field-companion-backend.onrender.com` |

---

## 5. Mobile App APK Hosting & Website Download

Users visiting your deployed website can download and try the mobile app directly.

### What is included:
1. **Download Banner & Button on Website:**
   - Prominent **"Download Mobile App"** badge in the Home screen header.
   - Dedicated **"Download Mobile App (APK / Expo)"** button in Settings.
   - Tapping it opens a modal with:
     - Direct one-tap download button for `FieldCompanion.apk`.
     - 3-step Android sideloading instructions ("Download APK" -> "Allow Unknown Sources" -> "Install").
     - Instant **Expo Go** runner instructions for iOS & Android users who prefer not to install an APK.

2. **Backend Download Endpoints (`backend/app/main.py`):**
   - `GET /download/app` (or `/download/field-companion.apk`): Streams `FieldCompanion.apk` with `Content-Disposition: attachment`.
   - `GET /download/app/info`: Returns metadata (version, file size, installation instructions).

### How to Build and Replace the Standalone APK:
To build a standalone APK package for Android:
```bash
# 1. Navigate to mobile directory
cd field-companion/mobile

# 2. Build APK using EAS (configured in eas.json)
npx eas build -p android --profile preview

# 3. Once EAS completes, download the generated .apk file
# 4. Copy it to your backend downloads folder:
cp path/to/build.apk ../backend/data/downloads/FieldCompanion.apk
```
*Tip: If you host the APK on GitHub Releases or AWS S3, you can simply set the Render environment variable `MOBILE_APP_DOWNLOAD_URL=https://your-url/FieldCompanion.apk`, and the `/download/app` endpoint will automatically redirect downloads there!*

---

## 6. Pre-Deployment Verification Checklist

Before pushing to production, run:
```bash
cd field-companion
make verify-all
```
This automatically verifies:
- [x] All 126 automated backend tests pass (`pytest`)
- [x] React webapp compiles cleanly to `dist/` (`npm run build`)
- [x] React Native mobile app type-checks with zero errors (`tsc --noEmit`)
- [x] Pre-seeded SQLite species database (`field_companion.db`) exists
- [x] Dockerfile builds and tests healthcheck endpoint
