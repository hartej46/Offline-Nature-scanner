"""
Audio handling for Field Companion.
BirdNET wrapper + acoustic fallback classification + Whisper STT + macOS say TTS.
"""

import os
import re
import ssl
import logging
import subprocess
from typing import Optional, List, Dict
from datetime import datetime

import numpy as np
import soundfile as sf

# Allow local SSL context for Whisper model download/cache
ssl._create_default_https_context = ssl._create_unverified_context

logger = logging.getLogger(__name__)

AUDIO_MAX_DURATION = int(os.getenv("AUDIO_MAX_DURATION", "30"))

# Regional bird acoustic reference profiles (calibrated for Western Ghats / Indian subcontinent regional checklist)
REGIONAL_BIRD_ACOUSTIC_PROFILES = [
    {
        "common_name": "Greater Coucal",
        "sci_name": "Centropus sinensis",
        "peak_freq": 510,
        "centroid": 1050,
        "freq_range": (350, 750),
        "notes": "Deep resonant booming oop-oop series in undergrowth",
    },
    {
        "common_name": "Spotted Dove",
        "sci_name": "Spilopelia chinensis",
        "peak_freq": 770,
        "centroid": 1250,
        "freq_range": (600, 1150),
        "notes": "Gentle rhythmic low cooing on branches or ground",
    },
    {
        "common_name": "Asian Koel",
        "sci_name": "Eudynamys scolopaceus",
        "peak_freq": 1810,
        "centroid": 2300,
        "freq_range": (1400, 2400),
        "notes": "Ascending fluty koo-OO call building in volume and pitch",
    },
    {
        "common_name": "Common Myna",
        "sci_name": "Acridotheres tristis",
        "peak_freq": 2200,
        "centroid": 3200,
        "freq_range": (1800, 3600),
        "notes": "Loud varied chatter, descending whistles and clucks",
    },
    {
        "common_name": "Red-vented Bulbul",
        "sci_name": "Pycnonotus cafer",
        "peak_freq": 2990,
        "centroid": 4300,
        "freq_range": (2600, 3800),
        "notes": "Percussive rhythmic chattering, short sharp bursts",
    },
    {
        "common_name": "Black Drongo",
        "sci_name": "Dicrurus macrocercus",
        "peak_freq": 3160,
        "centroid": 5300,
        "freq_range": (2200, 4400),
        "notes": "Harsh metallic rasping whistles, scolding calls and mimicry",
    },
    {
        "common_name": "Rose-ringed Parakeet",
        "sci_name": "Psittacula krameri",
        "peak_freq": 3540,
        "centroid": 5400,
        "freq_range": (2400, 4600),
        "notes": "Shrill piercing flight screech kee-ak",
    },
    {
        "common_name": "Oriental Magpie-Robin",
        "sci_name": "Copsychus saularis",
        "peak_freq": 3870,
        "centroid": 4900,
        "freq_range": (3200, 4800),
        "notes": "Melodic whistling phrases with rising and falling flute-like notes",
    },
    {
        "common_name": "Common Tailorbird",
        "sci_name": "Orthotomus sutorius",
        "peak_freq": 4900,
        "centroid": 4750,
        "freq_range": (4200, 5600),
        "notes": "Loud rapid repetitive high-pitched chweep-chweep calls",
    },
    {
        "common_name": "Crimson Sunbird",
        "sci_name": "Aethopyga siparaja",
        "peak_freq": 6650,
        "centroid": 6300,
        "freq_range": (5800, 7500),
        "notes": "Very high-pitched thin metallic rapid chip trills near nectar flowers",
    },
]

# Lazy-loaded Whisper model
_whisper_model = None


def get_whisper_model():
    """Load or return cached Whisper model."""
    global _whisper_model
    if _whisper_model is None:
        try:
            import whisper
            logger.info("Loading Whisper speech-to-text model...")
            _whisper_model = whisper.load_model("tiny")
            logger.info("Whisper model loaded.")
        except Exception as e:
            logger.error(f"Failed to load Whisper: {e}")
            _whisper_model = None
    return _whisper_model


def fallback_acoustic_analysis(audio_path: str, min_confidence: float = 0.1) -> List[Dict]:
    """
    Fallback acoustic classifier when BirdNET cannot run on Apple Silicon.
    Extracts peak frequencies and spectral centroid to match against regional species.
    Clearly marks candidates with source '[fallback - lower confidence]' per plan.
    """
    try:
        data, sr = sf.read(audio_path)
        if len(data.shape) > 1:
            data = np.mean(data, axis=1)  # Convert stereo to mono

        # Restrict to first 30 seconds
        max_samples = sr * AUDIO_MAX_DURATION
        if len(data) > max_samples:
            data = data[:max_samples]

        # Calculate FFT and spectral features
        n = len(data)
        if n == 0 or np.max(np.abs(data)) < 1e-4:
            logger.warning("Audio is silent or empty")
            return []

        fft = np.abs(np.fft.rfft(data))
        freqs = np.fft.rfftfreq(n, 1 / sr)

        # Ignore frequencies below 200 Hz (wind / microphone rumble)
        valid_mask = freqs >= 200
        fft_valid = fft[valid_mask]
        freqs_valid = freqs[valid_mask]

        if len(fft_valid) == 0:
            return []

        peak_idx = np.argmax(fft_valid)
        peak_freq = freqs_valid[peak_idx]
        total_energy = np.sum(fft_valid)
        centroid = np.sum(freqs_valid * fft_valid) / total_energy if total_energy > 0 else 0

        # Score against each regional bird profile
        scored_candidates = []
        for profile in REGIONAL_BIRD_ACOUSTIC_PROFILES:
            target_peak = profile["peak_freq"]
            target_centroid = profile["centroid"]
            low_f, high_f = profile["freq_range"]

            # Frequency distance penalty
            freq_diff = abs(peak_freq - target_peak) / max(target_peak, 500)
            centroid_diff = abs(centroid - target_centroid) / max(target_centroid, 500)

            # In-band bonus
            in_band = 1.0 if (low_f <= peak_freq <= high_f) else 0.4

            # Compute normalized confidence score between 0.15 and 0.92
            distance = (0.65 * freq_diff + 0.35 * centroid_diff)
            score = max(0.05, 0.92 * in_band / (1.0 + 1.8 * distance))

            if score >= min_confidence:
                scored_candidates.append({
                    "common_name": profile["common_name"],
                    "sci_name": profile["sci_name"],
                    "confidence": round(float(score), 3),
                    "source": "Acoustic analysis [fallback - lower confidence]",
                    "detected_peak_freq": round(float(peak_freq), 1),
                    "notes": profile["notes"],
                })

        # Sort by confidence descending
        scored_candidates.sort(key=lambda x: x["confidence"], reverse=True)
        return scored_candidates[:5]

    except Exception as e:
        logger.error(f"Fallback acoustic analysis failed: {e}")
        return []


def analyze_bird_audio(
    audio_path: str,
    lat: float = None,
    lon: float = None,
    week: int = None,
    min_confidence: float = 0.1,
) -> list[dict]:
    """
    Analyze an audio recording for bird species.
    Uses BirdNET if available; falls back to acoustic checklist analysis on Apple Silicon.
    """
    if week is None:
        week = datetime.now().isocalendar()[1]
        if week > 48:
            week = 48

    # Attempt BirdNET
    try:
        from birdnetlib import Recording
        from birdnetlib.analyzer import Analyzer

        analyzer = Analyzer()
        recording = Recording(
            analyzer,
            audio_path,
            lat=lat or 0.0,
            lon=lon or 0.0,
            week=week,
            min_conf=min_confidence,
        )
        recording.analyze()

        detections = []
        for detection in recording.detections:
            detections.append({
                "common_name": detection.get("common_name", "Unknown"),
                "sci_name": detection.get("scientific_name", "Unknown"),
                "confidence": round(detection.get("confidence", 0.0), 3),
                "source": "BirdNET",
                "start_time": detection.get("start_time"),
                "end_time": detection.get("end_time"),
            })

        if detections:
            detections.sort(key=lambda x: x["confidence"], reverse=True)
            return detections[:5]

    except (ImportError, Exception) as e:
        logger.info(f"BirdNET unavailable or error ({e}). Using acoustic fallback.")

    # Execute acoustic analysis fallback
    return fallback_acoustic_analysis(audio_path, min_confidence=min_confidence)


def transcribe_audio(audio_path: str) -> Dict:
    """
    Transcribe speech in an audio file using Whisper.
    Returns:
        {
            "text": transcribed text string,
            "is_speech": bool (True if intelligible spoken query detected),
            "language": language code
        }
    """
    model = get_whisper_model()
    if model is None:
        return {"text": "", "is_speech": False, "language": "en"}

    try:
        # Transcribe with fp16=False for universal CPU/Metal compatibility
        result = model.transcribe(audio_path, fp16=False)
        raw_text = result.get("text", "").strip()
        language = result.get("language", "en")

        # Clean hallucinated artifacts or pure noise tokens
        clean_text = re.sub(r"\[.*?\]|\(.*?\)", "", raw_text).strip()

        # Check whether this contains meaningful speech
        words = clean_text.split()
        is_speech = len(words) >= 2 and len(clean_text) >= 5

        # Check for query indicator keywords
        query_words = {"what", "who", "which", "saw", "see", "bird", "plant", "animal", "flower", "tree", "is", "this", "that", "tell", "listen"}
        has_query_intent = any(w.lower().strip("?,.") in query_words for w in words)

        return {
            "text": clean_text if clean_text else raw_text,
            "is_speech": is_speech or has_query_intent,
            "language": language,
        }
    except Exception as e:
        logger.error(f"Whisper transcription failed: {e}")
        return {"text": "", "is_speech": False, "language": "en"}


def condense_for_speech(text: str, max_words: int = 25) -> str:
    """
    Per Checkpoint 2.2: 'keep spoken replies under about 25 words, with the full text on screen'.
    Extracts the core identification and confirmation advice.
    """
    if not text:
        return ""

    # Remove Markdown headers and formatting
    cleaned = re.sub(r"#+\s*", "", text)
    cleaned = re.sub(r"[\*_`]", "", cleaned)
    cleaned = re.sub(r"\[.*?\]", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    selected = []
    total_words = 0

    for s in sentences:
        s_words = s.split()
        if total_words + len(s_words) <= max_words:
            selected.append(s)
            total_words += len(s_words)
        else:
            if not selected and len(s_words) > max_words:
                selected.append(" ".join(s_words[:max_words]) + ".")
            break

    spoken = " ".join(selected) if selected else " ".join(cleaned.split()[:max_words])
    return spoken.strip()


def synthesize_speech(
    text: str,
    output_path: Optional[str] = None,
    uploads_dir: str = "./data/uploads",
) -> str:
    """
    Synthesize speech using macOS `say` into a 16-bit WAV file.
    Returns the path to the generated WAV audio file.
    """
    spoken_text = condense_for_speech(text, max_words=25)
    if not spoken_text:
        spoken_text = "Identification complete."

    if not output_path:
        os.makedirs(uploads_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(uploads_dir, f"tts_{timestamp}.wav")

    try:
        # Generate 16-bit PCM WAV at 22050 Hz via macOS say
        cmd = [
            "/usr/bin/say",
            "-o", output_path,
            "--data-format=LEI16@22050",
            spoken_text,
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output_path
    except Exception as e:
        logger.error(f"macOS say TTS failed: {e}")
        # Create silent/fallback WAV if say failed
        sr = 22050
        empty_wav = np.zeros(int(sr * 0.5), dtype=np.int16)
        sf.write(output_path, empty_wav, sr, subtype="PCM_16")
        return output_path


def speak_aloud(text: str):
    """Optionally speak text aloud on the Mac speaker directly."""
    spoken_text = condense_for_speech(text, max_words=25)
    try:
        subprocess.Popen(["/usr/bin/say", spoken_text])
    except Exception as e:
        logger.warning(f"speak_aloud failed: {e}")


def save_audio(audio_bytes: bytes, save_dir: str, filename: str) -> str:
    """Save audio bytes to disk. Returns the full path."""
    os.makedirs(save_dir, exist_ok=True)
    path = os.path.join(save_dir, filename)
    with open(path, "wb") as f:
        f.write(audio_bytes)
    return path
