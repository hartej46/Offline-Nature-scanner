# Offline Nature Scanner — Production Deployment Guide

A complete, production-ready guide for deploying the **Offline Nature Scanner (Field Companion)** to **Render**, configuring model weights downloads via direct internet URL (zero cloud model fees), and distributing the offline mobile app.

---

## 1. System Architecture

```
                            +-------------------------------------------------------+
                            |                  RENDER CLOUD                         |
                            |                                                       |
  [ Mobile / Android ]      |   +-----------------------------------------------+   |
          |                 |   |  FastAPI Backend (Docker Web Service)         |   |
          |-- Download APK -|-->|  - GET /download/app (FieldCompanion.apk)     |   |
          |                 |   |  - Audio (BirdNET & Acoustic features)        |   |
          |-- Model Redirect|-->|  - GET /model/download/{id} -> Model URL      |   |
          |                 |   |  - Regional Checklist & Journal (SQLite)      |   |
          |                 |   +-----------------------+-----------------------+   |
          |                 |                           |                           |
  [ Web Browser ]           |                           v                           |
          |                 |   +-----------------------------------------------+   |
          +--- HTTPS ------->   |  Landing Page (Render Static Site / PWA)      |   |
                            |   |  - 100% Offline Cached Service Worker (sw.js) |   |
                            |   |  - Direct One-Tap Android APK Download Button |   |
                            |   |  - Interactive Mobile App Feature Simulator   |   |
                            |   |  - Expo Go Quick-Test & Installation Guides   |   |
                            |   +-----------------------------------------------+   |
                            |                                                       |
                            +---------------------------|---------------------------+
                                                        |
                                                        | Redirect to Direct Weights URL
                                                        v
                                        +-------------------------------+
                                        | Model Weights CDN / S3 / HF   |
                                        | (Downloaded to Phone Once)    |
                                        | - 100% On-Device Neural Model |
                                        | - Zero Cloud Inference Calls  |
                                        +-------------------------------+
```

---

## 2. Model Architecture: Direct Internet Download via URL

**You do NOT need any cloud AI API (no Groq, no OpenAI, no Gemini, and zero monthly API costs).**

Field Companion is designed so model weights are downloaded directly from the internet onto the mobile phone and executed locally on-device:

### How It Works:
1. **Configure Your Model Download URL:**
   In your Render environment (or backend `.env`), set `MODEL_DOWNLOAD_URL` to your model weights file URL:
   ```env
   MODEL_DOWNLOAD_URL=https://huggingface.co/bartowski/gemma-2-2b-it-GGUF/resolve/main/gemma-2-2b-it-Q4_K_M.gguf
   ```
   *(You can use any direct HTTP/HTTPS link: Hugging Face direct link, AWS S3, Google Cloud Storage, GitHub Release, or your own server).*

2. **One-Time Download Over Internet:**
   - The user opens the mobile app while connected to Wi-Fi/Internet.
   - The app requests `GET /model/download/gemma4:e2b` from your backend, which redirects directly (HTTP 307) to your `MODEL_DOWNLOAD_URL`.
   - The phone downloads the GGUF model package directly into its local document directory (`FileSystem.documentDirectory + "models/"`).

3. **100% Offline in the Wild:**
   - Once the download is complete, the model weights live permanently on the mobile device.
   - Users can walk deep into the woods, mountains, or trails with **airplane mode on / zero cellular signal**.
   - All species recognition and reasoning runs locally on the phone's processor!

---

## 3. Deploying to Render via Blueprint (`render.yaml`)

We have created an automated **Render Blueprint** in `render.yaml` for 1-click deployment.

### Steps:
1. Push your repository to GitHub:
   ```bash
   git push origin main
   ```
   *(Repo: `https://github.com/hartej46/Offline-Nature-scanner.git`)*
2. Log into the [Render Dashboard](https://dashboard.render.com).
3. Click **New +** -> **Blueprint**.
4. Connect your `Offline-Nature-scanner` repository.
5. Render will automatically parse `render.yaml` and configure two services:
   - **`field-companion-backend`**: Docker Web Service running FastAPI.
   - **`field-companion-web`**: Static Site hosting the mobile download landing page.
6. Under environment variables, review `MODEL_DOWNLOAD_URL` (defaults to Hugging Face Gemma 4 GGUF, or replace with your own model URL).
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
  | `PORT` | `8000` | Port assigned dynamically by Render |
  | `DATA_DIR` | `/app/data` | Storage directory for SQLite and uploads |
  | `DB_PATH` | `/app/data/field_companion.db` | Pre-seeded 731-species regional checklist |
  | `MODEL_DOWNLOAD_URL` | `https://huggingface.co/.../model.gguf` | Direct internet model download URL |
  | `REGION_BBOX` | `6.5,68.1,35.7,97.4` | Regional geographic bounding box |
  | `MOBILE_APP_DOWNLOAD_URL` | *(optional)* | External link if hosting APK on S3/GitHub |
- **Persistent Disk (Optional):** Attach a 10 GB disk mounted at `/app/data` to persist observations and recordings.

### Service 2: Web Landing Page (Static Site)
- **Name:** `field-companion-web`
- **Root Directory:** (leave blank or `field-companion`)
- **Build Command:** `cd field-companion/webapp && npm install && npm run build`
- **Publish Directory:** `field-companion/webapp/dist`
- **Environment Variables:**
  | Variable | Value |
  |---|---|
  | `VITE_API_BASE` | `https://field-companion-backend.onrender.com` |

---

## 5. Mobile App Distribution & Landing Page

### 1. Web Landing Page Features
- **100% Offline-Capable (`sw.js`):** Built as an offline PWA that caches its assets so the landing page opens without internet.
- **Direct APK Download Button:** One-tap button that downloads `FieldCompanion.apk` directly from your Render server (`/download/app`).
- **Interactive Device Preview:** Simulated phone showing live Listen, Photo, Diary, and Model Pack views.
- **3-Step Sideloading Guide:** Illustrated Android instructions (*Download APK → Allow Unknown Sources → Install*).
- **Expo Go Instant Runner:** Scan QR code or run `npx expo start --go` to test instantly on iPhone or Android without sideloading.

### 2. Backend Download Endpoints
- `GET /download/app` (or `/download/field-companion.apk`): Streams `FieldCompanion.apk` with `Content-Disposition: attachment`.
- `GET /download/app/info`: Returns metadata (app version, file size, installation instructions).
- `GET /model/download/{model_id}`: Redirects (HTTP 307) directly to your `MODEL_DOWNLOAD_URL`.

### 3. How to Build and Replace the Standalone APK
To build a standalone APK for Android using Expo EAS:
```bash
# 1. Navigate to the mobile directory
cd field-companion/mobile

# 2. Build standalone APK with EAS
npx eas build -p android --profile preview

# 3. Once EAS completes, copy the generated .apk to your backend downloads:
cp path/to/build.apk ../backend/data/downloads/FieldCompanion.apk
```

*Tip: If you prefer hosting the APK on GitHub Releases or AWS S3, simply set the Render environment variable `MOBILE_APP_DOWNLOAD_URL=https://github.com/<user>/<repo>/releases/download/v1.0.0/FieldCompanion.apk`. The `/download/app` route will automatically redirect downloads there!*

---

## 6. Pre-Deployment Verification Checklist

Before pushing to production, run:
```bash
cd field-companion
make verify-all
```
This automatically verifies:
- [x] All 128 automated backend unit & integration tests pass (`pytest`)
- [x] Custom model download URL redirect verified
- [x] Web landing page compiles cleanly to `dist/` with service worker (`npm run build`)
- [x] React Native mobile app type-checks with zero errors (`tsc --noEmit`)
- [x] Pre-seeded SQLite species database (`field_companion.db`) exists
- [x] Dockerfile builds cleanly for Render container deployment
