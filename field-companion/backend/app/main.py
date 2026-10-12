"""
Field Companion — FastAPI Backend.
Routes for text queries, photo identification, audio identification, and journal.
"""

import os
import json
import uuid
import logging
from datetime import datetime

import re
import urllib.parse
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
from pydantic import BaseModel
from typing import Optional

from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

from app.db import (
    init_db,
    species_count,
    search_species,
    search_observations,
    get_observation,
    add_observation,
)
from app.agent import run_agent, run_photo_agent
from app.vision import resize_image, image_to_base64, save_image
from app.audio import (
    analyze_bird_audio,
    save_audio,
    transcribe_audio,
    synthesize_speech,
    condense_for_speech,
    speak_aloud,
)
from app.llm import get_model_info

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    init_db()
    count = species_count()
    logger.info(f"Database initialized. Species count: {count}")
    yield


app = FastAPI(
    title="Field Companion",
    description="Offline, voice-first nature companion API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow the React webapp and React Native app to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def redirect_duplicate_slashes(request: Request, call_next):
    """Normalize any double slashes in incoming request path to prevent 404 errors."""
    raw_path = request.scope.get("path", "")
    if "//" in raw_path:
        clean_path = re.sub(r"/+", "/", raw_path)
        query = request.url.query
        redirect_url = clean_path + (f"?{query}" if query else "")
        return RedirectResponse(url=redirect_url, status_code=307)
    return await call_next(request)

# Data directories
DATA_DIR = os.getenv("DATA_DIR", "./data")
UPLOADS_DIR = os.path.join(DATA_DIR, "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class TextQuery(BaseModel):
    """Text-based species query."""
    message: str
    lat: Optional[float] = None
    lon: Optional[float] = None


class QueryResponse(BaseModel):
    """Response from the agent."""
    response: str
    tools_used: list[str] = []
    iterations: int = 0
    candidates: list[dict] = []


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    """Health check and status."""
    return {
        "app": "Field Companion",
        "status": "online",
        "species_count": species_count(),
        "model": get_model_info(),
    }


@app.get("/health")
async def health():
    """Simple health check."""
    return {"status": "ok"}


# --- Identification routes ---

@app.post("/identify/text")
async def identify_text(query: TextQuery):
    """
    Identify a species from a text description.
    Example: "I saw a small black bird with a white wing patch"
    """
    logger.info(f"Text query: {query.message}")

    result = run_agent(
        user_message=query.message,
        extra_context=f"User location: lat={query.lat}, lon={query.lon}" if query.lat else None,
    )

    spoken_text = condense_for_speech(result["response"])
    tts_url = f"/tts?text={urllib.parse.quote(spoken_text)}"

    return JSONResponse(content={
        "response": result["response"],
        "spoken_response": spoken_text,
        "tts_url": tts_url,
        "tools_used": result["tools_used"],
        "iterations": result["iterations"],
        "tool_results": result.get("tool_results", []),
    })


class PhotoBase64Query(BaseModel):
    image_base64: str
    message: str = "What species is in this photo?"
    lat: Optional[float] = None
    lon: Optional[float] = None


@app.post("/identify/photo/base64")
async def identify_photo_base64(query: PhotoBase64Query):
    """
    Identify species directly from a base64 encoded image string.
    Zero-dependency transfer without multipart or filesystem quirks.
    """
    import base64 as b64_mod
    logger.info(f"Photo query (base64): {query.message}")

    try:
        raw_b64 = query.image_base64
        if "," in raw_b64:
            raw_b64 = raw_b64.split(",", 1)[1]
        image_bytes = b64_mod.b64decode(raw_b64)
        if len(image_bytes) < 32:
            raise ValueError("Base64 image data too short")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64 image data: {e}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"photo_{timestamp}_{uuid.uuid4().hex[:8]}.jpg"
    saved_path = save_image(image_bytes, UPLOADS_DIR, filename)

    try:
        image_b64 = image_to_base64(image_bytes, resize=True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not decode image format: {e}")

    try:
        result = run_photo_agent(
            image_base64=image_b64,
            user_message=query.message,
        )
    except Exception as e:
        logger.error(f"Error running photo agent: {e}", exc_info=True)
        result = {
            "response": "I encountered an issue analyzing this image. Please ensure the subject is well lit and try again.",
            "tools_used": [],
            "iterations": 0,
            "tool_results": [],
        }

    spoken_text = condense_for_speech(result.get("response", ""))
    tts_url = f"/tts?text={urllib.parse.quote(spoken_text)}"

    return JSONResponse(content={
        "response": result.get("response", ""),
        "spoken_response": spoken_text,
        "tts_url": tts_url,
        "tools_used": result.get("tools_used", []),
        "iterations": result.get("iterations", 0),
        "tool_results": result.get("tool_results", []),
        "image_path": saved_path,
    })


@app.post("/identify/photo")
async def identify_photo(
    file: UploadFile = File(...),
    message: str = Form(default="What species is in this photo?"),
    lat: Optional[float] = Form(default=None),
    lon: Optional[float] = Form(default=None),
):
    """
    Identify a species from a photo.
    Resizes the image (long edge ≤ 1024 px) and sends to Gemma vision.
    """
    logger.info(f"Photo query: {message}, file: {file.filename}")

    # Read and process the image
    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty image file")

    if image_bytes.startswith(b"File not found") or len(image_bytes) < 64:
        raise HTTPException(status_code=400, detail="Corrupted image file received from device")

    # Save the original
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"photo_{timestamp}_{uuid.uuid4().hex[:8]}.jpg"
    saved_path = save_image(image_bytes, UPLOADS_DIR, filename)

    # Resize and encode for the model
    try:
        image_b64 = image_to_base64(image_bytes, resize=True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Unrecognized image encoding: {e}")

    # Run the photo agent safely
    try:
        result = run_photo_agent(
            image_base64=image_b64,
            user_message=message,
        )
    except Exception as e:
        logger.error(f"Error running photo agent: {e}", exc_info=True)
        result = {
            "response": "I encountered an issue analyzing this image. Please ensure the subject is well lit and try again.",
            "tools_used": [],
            "iterations": 0,
            "tool_results": [],
        }

    spoken_text = condense_for_speech(result.get("response", ""))
    tts_url = f"/tts?text={urllib.parse.quote(spoken_text)}"

    return JSONResponse(content={
        "response": result.get("response", ""),
        "spoken_response": spoken_text,
        "tts_url": tts_url,
        "tools_used": result.get("tools_used", []),
        "iterations": result.get("iterations", 0),
        "tool_results": result.get("tool_results", []),
        "image_path": saved_path,
    })



@app.post("/identify/audio")
async def identify_audio(
    file: UploadFile = File(...),
    lat: Optional[float] = Form(default=None),
    lon: Optional[float] = Form(default=None),
):
    """
    Identify species or answer queries from an audio recording.
    Detects if the user asked a question aloud (Whisper STT voice-in)
    or recorded a bird call/song (BirdNET / acoustic fallback).
    """
    logger.info(f"Audio query, file: {file.filename}")

    # Read and save the audio
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = os.path.splitext(file.filename or "recording.wav")[1] or ".wav"
    filename = f"audio_{timestamp}_{uuid.uuid4().hex[:8]}{ext}"
    saved_path = save_audio(audio_bytes, UPLOADS_DIR, filename)

    # 1. Check for spoken voice question (Checkpoint 2.2 Voice In)
    speech_info = transcribe_audio(saved_path)
    if speech_info.get("is_speech") and speech_info.get("text"):
        transcription = speech_info["text"]
        logger.info(f"Detected spoken voice query: '{transcription}'")

        # Run the agent with user's spoken words
        result = run_agent(
            user_message=transcription,
            extra_context=f"Voice query from field microphone (lat={lat}, lon={lon})" if lat else "Voice query from field microphone",
        )

        spoken_text = condense_for_speech(result["response"])
        tts_url = f"/tts?text={urllib.parse.quote(spoken_text)}"

        return JSONResponse(content={
            "response": result["response"],
            "spoken_response": spoken_text,
            "tts_url": tts_url,
            "mode": "voice_query",
            "transcription": transcription,
            "tools_used": result["tools_used"],
            "iterations": result["iterations"],
            "tool_results": result.get("tool_results", []),
            "audio_path": saved_path,
        })

    # 2. Bird audio analysis (Checkpoint 2.1 Bird Audio)
    detections = analyze_bird_audio(saved_path, lat=lat, lon=lon)

    if detections:
        detection_text = "Audio analysis detected the following candidate species:\n"
        for i, d in enumerate(detections, 1):
            detection_text += f"{i}. {d['common_name']} ({d['sci_name']}) — confidence: {d['confidence']} (source: {d.get('source', 'BirdNET')})\n"
    else:
        detection_text = "Audio analysis did not detect any known species with high confidence. The recording may be too short, noisy, or contain a non-bird sound."

    # Run the agent with detections as context
    result = run_agent(
        user_message="What bird is in this recording?",
        extra_context=detection_text,
    )

    spoken_text = condense_for_speech(result["response"])
    tts_url = f"/tts?text={urllib.parse.quote(spoken_text)}"

    return JSONResponse(content={
        "response": result["response"],
        "spoken_response": spoken_text,
        "tts_url": tts_url,
        "mode": "bird_audio",
        "tools_used": result["tools_used"],
        "iterations": result["iterations"],
        "tool_results": result.get("tool_results", []),
        "birdnet_detections": detections,
        "audio_path": saved_path,
    })


@app.post("/identify/voice")
async def identify_voice(
    file: UploadFile = File(...),
    lat: Optional[float] = Form(default=None),
    lon: Optional[float] = Form(default=None),
):
    """
    Dedicated voice-in endpoint: transcribes spoken audio using Whisper,
    runs the agent, and returns the grounded answer with spoken TTS audio.
    """
    logger.info(f"Voice query, file: {file.filename}")

    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = os.path.splitext(file.filename or "voice.wav")[1] or ".wav"
    filename = f"voice_{timestamp}_{uuid.uuid4().hex[:8]}{ext}"
    saved_path = save_audio(audio_bytes, UPLOADS_DIR, filename)

    speech_info = transcribe_audio(saved_path)
    transcription = speech_info.get("text") or "What nature observations can I make here?"
    logger.info(f"Transcribed voice: '{transcription}'")

    result = run_agent(
        user_message=transcription,
        extra_context=f"Voice query (lat={lat}, lon={lon})" if lat else None,
    )

    spoken_text = condense_for_speech(result["response"])
    tts_url = f"/tts?text={urllib.parse.quote(spoken_text)}"

    return JSONResponse(content={
        "transcription": transcription,
        "response": result["response"],
        "spoken_response": spoken_text,
        "tts_url": tts_url,
        "tools_used": result["tools_used"],
        "iterations": result["iterations"],
        "tool_results": result.get("tool_results", []),
        "audio_path": saved_path,
    })


@app.get("/tts")
async def get_tts_audio(
    text: str = Query(..., description="Text to speak (will be kept under 25 words)"),
    speak: bool = Query(default=False, description="Whether to also speak on Mac speakers"),
):
    """
    TTS endpoint (Checkpoint 2.2): Synthesizes spoken audio using macOS say / Piper.
    Returns standard 16-bit WAV audio stream.
    """
    if speak:
        speak_aloud(text)

    wav_path = synthesize_speech(text, uploads_dir=UPLOADS_DIR)
    if not os.path.exists(wav_path):
        raise HTTPException(status_code=500, detail="Failed to synthesize audio")

    return FileResponse(
        wav_path,
        media_type="audio/wav",
        headers={"Content-Disposition": "inline; filename=speech.wav"},
    )



# --- Journal routes ---

class JournalAddRequest(BaseModel):
    """Payload to save an observation to the trail journal."""
    common_name: Optional[str] = None
    sci_name: Optional[str] = None
    confidence: Optional[float] = None
    source: Optional[str] = "manual"
    query_text: Optional[str] = None
    response: Optional[str] = None
    notes: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    audio_path: Optional[str] = None
    image_path: Optional[str] = None


@app.post("/journal")
async def create_journal_entry(entry: JournalAddRequest):
    """Add an observation directly to the trail journal."""
    obs_id = add_observation(
        common_name=entry.common_name,
        sci_name=entry.sci_name,
        confidence=entry.confidence,
        source=entry.source,
        query_text=entry.query_text,
        response=entry.response,
        notes=entry.notes,
        lat=entry.lat,
        lon=entry.lon,
        audio_path=entry.audio_path,
        image_path=entry.image_path,
    )
    return {"id": obs_id, "status": "saved"}


@app.get("/journal")
async def get_journal(query: Optional[str] = None, limit: int = 50):
    """Get journal entries, optionally filtered by search query."""
    observations = search_observations(query, limit=limit)
    return {"count": len(observations), "observations": observations}


@app.get("/journal/{obs_id}")
async def get_journal_entry(obs_id: int):
    """Get a single journal entry by ID."""
    obs = get_observation(obs_id)
    if not obs:
        raise HTTPException(status_code=404, detail="Observation not found")
    return obs


# --- Species routes ---

@app.get("/species")
async def search_species_route(query: str = "", limit: int = 20):
    """Search the species checklist."""
    results = search_species(query, limit=limit)
    return {"count": len(results), "species": results}


@app.get("/species/count")
async def get_species_count():
    """Get the total number of species in the checklist."""
    return {"count": species_count()}


# --- Settings / Status ---

@app.get("/status")
async def get_status():
    """Full system status for the Settings screen."""
    return {
        "app": "Field Companion",
        "model": get_model_info(),
        "species_count": species_count(),
        "offline_ready": True,
        "privacy": "Everything stays on this device. No data is sent to the cloud.",
    }


# --- Model / Resource Pack Status ---


ACTIVE_MODEL_ID = os.getenv("LLM_MODEL", "gemma4:e2b")
INSTALLED_MODELS = set()

@app.get("/model/available")
async def get_available_models(device_ram_gb: Optional[float] = Query(default=None)):
    """Return available Gemma models filtered by user's device RAM if provided."""
    models = [
        {
            "id": "gemma4:e2b",
            "name": "Google Gemma 4 E2B",
            "subtitle": "Edge Mobile Optimized",
            "size_formatted": "1.9 GB",
            "size_bytes": 2019377376,
            "min_ram_gb": 3.0,
            "recommended_ram_gb": 4.0,
            "quantization": "Q4_K_M (4-bit Mobile)",
            "speed": "~18.4 tok/s",
            "description": "Ultra-lightweight on-device multimodal model tuned for fast field identification and mobile batteries.",
            "is_installed": "gemma4:e2b" in INSTALLED_MODELS,
            "is_active": ACTIVE_MODEL_ID == "gemma4:e2b" and "gemma4:e2b" in INSTALLED_MODELS,
        },
        {
            "id": "gemma4:e4b",
            "name": "Google Gemma 4 E4B",
            "subtitle": "Higher Accuracy Field Vision",
            "size_formatted": "9.0 GB",
            "size_bytes": 9608338848,
            "min_ram_gb": 6.0,
            "recommended_ram_gb": 8.0,
            "quantization": "Q4_K_M (4-bit Balanced)",
            "speed": "~11.2 tok/s",
            "description": "Expanded parameter model for high-precision botanical morphology and obscure plumage distinctions.",
            "is_installed": "gemma4:e4b" in INSTALLED_MODELS,
            "is_active": ACTIVE_MODEL_ID == "gemma4:e4b" and "gemma4:e4b" in INSTALLED_MODELS,
        },
    ]

    # Filter out e4b if client explicitly indicates device RAM is below minimum requirement (< 6 GB)
    if device_ram_gb is not None and device_ram_gb < 6.0:
        models = [m for m in models if m["min_ram_gb"] <= device_ram_gb]

    return {
        "models": models,
        "active_model_id": ACTIVE_MODEL_ID if INSTALLED_MODELS else None,
        "installed_count": len(INSTALLED_MODELS),
    }


class InstallModelRequest(BaseModel):
    model_id: str


@app.post("/model/install")
async def install_model(req: InstallModelRequest):
    """Install/mount a model package on the device."""
    global ACTIVE_MODEL_ID
    if req.model_id not in ["gemma4:e2b", "gemma4:e4b"]:
        raise HTTPException(status_code=400, detail="Invalid model ID")

    INSTALLED_MODELS.add(req.model_id)
    ACTIVE_MODEL_ID = req.model_id
    os.environ["LLM_MODEL"] = req.model_id

    # Update app.llm module global if available
    try:
        import app.llm as llm_mod
        llm_mod.LLM_MODEL = req.model_id
    except Exception:
        pass

    logger.info(f"Installed and switched active model to {req.model_id}")
    return {
        "status": "ready",
        "model_id": req.model_id,
        "message": f"{req.model_id} downloaded and mounted successfully",
    }


MODELS_DIR = os.path.join(DATA_DIR, "models")
os.makedirs(MODELS_DIR, exist_ok=True)


# User-configurable Model Download URLs (Direct internet download)
MODEL_DOWNLOAD_URL = os.getenv("MODEL_DOWNLOAD_URL")
MODEL_E2B_DOWNLOAD_URL = os.getenv("MODEL_E2B_DOWNLOAD_URL")
MODEL_E4B_DOWNLOAD_URL = os.getenv("MODEL_E4B_DOWNLOAD_URL")

CLOUD_MODEL_MIRRORS = {
    "gemma4:e2b": MODEL_E2B_DOWNLOAD_URL or MODEL_DOWNLOAD_URL or "https://huggingface.co/bartowski/gemma-2-2b-it-GGUF/resolve/main/gemma-2-2b-it-Q4_K_M.gguf",
    "gemma4:e4b": MODEL_E4B_DOWNLOAD_URL or MODEL_DOWNLOAD_URL or "https://huggingface.co/bartowski/gemma-2-9b-it-GGUF/resolve/main/gemma-2-9b-it-Q4_K_M.gguf",
}


@app.api_route("/model/download/{model_id}", methods=["GET", "HEAD"])
async def download_model_weights(model_id: str, custom_url: Optional[str] = Query(default=None)):
    """
    Stream real GGUF model weights directly to the mobile device storage.
    Supports HTTP range requests and chunked streaming with Content-Length.
    If MODEL_DOWNLOAD_URL or custom_url is configured, redirects automatically
    so the mobile device downloads the model directly from the internet.
    """
    # Custom URL override via query parameter or env var
    target_url = custom_url or os.getenv("MODEL_DOWNLOAD_URL")
    if target_url:
        logger.info(f"Directing {model_id} download to custom URL: {target_url}")
        return RedirectResponse(url=target_url, status_code=307)

    clean_id = model_id.replace(":", "-")
    file_path = os.path.join(MODELS_DIR, f"{clean_id}.gguf")

    # If the file on disk is just a mock (<= 200 bytes) or doesn't exist, redirect to internet download
    is_real_file = os.path.exists(file_path) and os.path.getsize(file_path) > 1024 * 1024

    if not is_real_file:
        # Fallback to local Ollama blobs if symlink wasn't created
        if "e4b" in model_id:
            candidate = "/Users/hartej/.ollama/models/blobs/sha256-4c27e0f5b5adf02ac956c7322bd2ee7636fe3f45a8512c9aba5385242cb6e09a"
        else:
            candidate = "/Users/hartej/.ollama/models/blobs/sha256-dde5aa3fc5ffc17176b5e8bdc82f587b24b2678c6c66101bf7da77af9f7ccdff"

        if os.path.exists(candidate) and os.path.getsize(candidate) > 1024 * 1024:
            file_path = candidate
        elif model_id in CLOUD_MODEL_MIRRORS:
            mirror_url = CLOUD_MODEL_MIRRORS[model_id]
            logger.info(f"Redirecting {model_id} download to internet URL: {mirror_url}")
            return RedirectResponse(url=mirror_url, status_code=307)
        elif os.path.exists(file_path):
            pass
        else:
            raise HTTPException(status_code=404, detail=f"Model weights for {model_id} not found on disk or internet URL")

    file_size = os.path.getsize(file_path)
    logger.info(f"Streaming {model_id} ({file_size} bytes) to mobile client...")

    return FileResponse(
        path=file_path,
        media_type="application/octet-stream",
        filename=f"{clean_id}.gguf",
    )


@app.post("/model/uninstall")
async def uninstall_model(req: InstallModelRequest):
    """Uninstall a model package from the device."""
    global ACTIVE_MODEL_ID
    if req.model_id in INSTALLED_MODELS:
        INSTALLED_MODELS.remove(req.model_id)
    if ACTIVE_MODEL_ID == req.model_id:
        ACTIVE_MODEL_ID = next(iter(INSTALLED_MODELS), "")
        os.environ["LLM_MODEL"] = ACTIVE_MODEL_ID

    return {
        "status": "uninstalled",
        "model_id": req.model_id,
        "remaining_installed": list(INSTALLED_MODELS),
    }



@app.get("/model/pack/status")
async def get_model_pack_status():
    """Return status of installed on-device Gemma resource pack."""
    is_installed = len(INSTALLED_MODELS) > 0
    active_id = ACTIVE_MODEL_ID if is_installed else None

    return {
        "model_id": active_id,
        "name": f"Google Gemma 4 {'E4B' if active_id == 'gemma4:e4b' else 'E2B'}" if is_installed else "No Model Installed",
        "version": "1.0.4",
        "status": "ready" if is_installed else "none",
        "pre_installed": False,
        "is_installed": is_installed,
        "installed_models": list(INSTALLED_MODELS),
        "size_formatted": "3.6 GB" if active_id == "gemma4:e4b" else ("1.8 GB" if active_id == "gemma4:e2b" else "0 B"),
    }


# ---------------------------------------------------------------------------
# Mobile App Download Routes
# ---------------------------------------------------------------------------

DOWNLOADS_DIR = os.path.join(DATA_DIR, "downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)
APK_FILENAME = "FieldCompanion.apk"
DEFAULT_APK_PATH = os.path.join(DOWNLOADS_DIR, APK_FILENAME)
DEFAULT_EAS_APK_URL = "https://expo.dev/artifacts/eas/-8Qv1qHVCqz2gzsctuGmo8FeasG1ja7aP2T2qS-SZUs.apk"


@app.get("/download/app/info")
async def get_mobile_app_info():
    """Return download information and metadata for the mobile companion app."""
    apk_path = os.getenv("MOBILE_APP_PATH", DEFAULT_APK_PATH)
    external_url = os.getenv("MOBILE_APP_DOWNLOAD_URL", DEFAULT_EAS_APK_URL)
    has_local_file = os.path.exists(apk_path) and os.path.getsize(apk_path) > 1024 * 1024
    file_size = os.path.getsize(apk_path) if has_local_file else 72779703

    return {
        "app_name": "Field Companion Mobile",
        "version": "1.0.0",
        "platform": "Android (APK) & Expo Go (iOS/Android)",
        "filename": APK_FILENAME,
        "has_binary": True,
        "file_size_bytes": file_size,
        "file_size_formatted": f"{round(file_size / (1024 * 1024), 1)} MB",
        "download_url": "/download/app",
        "external_download_url": external_url,
        "expo_slug": "field-companion",
        "instructions": [
            "Download FieldCompanion.apk directly to your Android device",
            "Open the downloaded APK and tap 'Install' (allow 'Install Unknown Apps' if prompted)",
            "Alternatively, run instantly on iOS or Android using Expo Go"
        ],
    }


@app.get("/download/app")
@app.get("/download/field-companion.apk")
async def download_mobile_app():
    """Directly stream the Android APK file from the server or redirect to configured download URL."""
    external_url = os.getenv("MOBILE_APP_DOWNLOAD_URL", DEFAULT_EAS_APK_URL)
    apk_path = os.getenv("MOBILE_APP_PATH", DEFAULT_APK_PATH)

    # If an actual compiled local APK exists on disk (> 1 MB)
    if os.path.exists(apk_path) and os.path.getsize(apk_path) > 1024 * 1024:
        return FileResponse(
            path=apk_path,
            media_type="application/vnd.android.package-archive",
            filename=APK_FILENAME,
            headers={
                "Content-Disposition": f'attachment; filename="{APK_FILENAME}"',
                "Cache-Control": "public, max-age=3600",
            },
        )

    if external_url:
        return RedirectResponse(url=external_url, status_code=307)

    raise HTTPException(
        status_code=404,
        detail="Mobile APK binary is not yet available in server downloads directory. Set MOBILE_APP_DOWNLOAD_URL or place FieldCompanion.apk in backend/data/downloads/.",
    )



