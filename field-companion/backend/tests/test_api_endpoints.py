"""
Comprehensive integration and edge-case tests for FastAPI routes (app.main).
Covers all endpoints:
- GET /
- GET /health
- GET /status
- GET /species
- GET /species/count
- GET /journal
- POST /journal
- GET /journal/{obs_id}
- GET /tts
- POST /identify/text
- POST /identify/photo
- POST /identify/audio
- POST /identify/voice
- CORS headers and validation edge cases (400, 404, 422).
"""

import io
import pytest
from unittest.mock import patch


class TestStatusAndHealthRoutes:
    def test_root_endpoint(self, client):
        """GET / returns app metadata, status, species count, and model info."""
        res = client.get("/")
        assert res.status_code == 200
        data = res.json()
        assert data["app"] == "Field Companion"
        assert data["status"] == "online"
        assert data["species_count"] >= 100
        assert "model" in data

    def test_health_endpoint(self, client):
        """GET /health returns status: ok."""
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json() == {"status": "ok"}

    def test_status_endpoint(self, client):
        """GET /status returns system readiness for SettingsScreen."""
        res = client.get("/status")
        assert res.status_code == 200
        data = res.json()
        assert data["offline_ready"] is True
        assert data["species_count"] >= 100
        assert "privacy" in data

    def test_cors_headers(self, client):
        """FastAPI must include CORS allow headers for web & mobile frontends."""
        res = client.get("/health", headers={"Origin": "http://localhost:5173"})
        assert res.status_code == 200
        assert res.headers.get("access-control-allow-origin") in ("*", "http://localhost:5173")


class TestSpeciesEndpoints:
    def test_species_search_all(self, client):
        """GET /species without query returns list of species up to limit."""
        res = client.get("/species?limit=10")
        assert res.status_code == 200
        data = res.json()
        assert "species" in data
        assert len(data["species"]) <= 10
        assert data["count"] <= 10

    def test_species_search_by_name(self, client):
        """GET /species with specific query filters correctly."""
        res = client.get("/species?query=Bulbul")
        assert res.status_code == 200
        data = res.json()
        assert data["count"] > 0
        names = [s["common_name"].lower() for s in data["species"]]
        assert any("bulbul" in n for n in names)

    def test_species_search_nonexistent(self, client):
        """GET /species with non-existent query returns empty list."""
        res = client.get("/species?query=NonExistentSpecies_xyz987")
        assert res.status_code == 200
        data = res.json()
        assert data["count"] == 0
        assert data["species"] == []

    def test_species_count(self, client):
        """GET /species/count returns positive integer count >= 100."""
        res = client.get("/species/count")
        assert res.status_code == 200
        data = res.json()
        assert "count" in data
        assert data["count"] >= 100


class TestJournalEndpoints:
    def test_create_and_get_journal_entry(self, client):
        """POST /journal creates observation, GET /journal/{id} retrieves it."""
        payload = {
            "common_name": "Oriental Magpie-Robin",
            "sci_name": "Copsychus saularis",
            "confidence": 0.95,
            "source": "photo",
            "notes": "Spotted singing on garden perch",
            "lat": 15.2993,
            "lon": 74.1240,
        }
        res = client.post("/journal", json=payload)
        assert res.status_code == 200
        body = res.json()
        assert "id" in body
        assert body["status"] == "saved"
        obs_id = body["id"]

        # Retrieve by ID
        get_res = client.get(f"/journal/{obs_id}")
        assert get_res.status_code == 200
        obs = get_res.json()
        assert obs["id"] == obs_id
        assert obs["common_name"] == "Oriental Magpie-Robin"
        assert obs["notes"] == "Spotted singing on garden perch"
        assert obs["lat"] == 15.2993

    def test_create_journal_minimal(self, client):
        """POST /journal accepts payload with minimal/optional fields."""
        res = client.post("/journal", json={"notes": "Rustling leaves heard"})
        assert res.status_code == 200
        assert res.json()["status"] == "saved"

    def test_get_journal_nonexistent_id(self, client):
        """GET /journal/{id} for non-existent observation returns 404."""
        res = client.get("/journal/99999999")
        assert res.status_code == 404
        assert res.json()["detail"] == "Observation not found"

    def test_get_journal_invalid_id_type(self, client):
        """GET /journal/not-an-int returns 422 Unprocessable Entity."""
        res = client.get("/journal/invalid_id_string")
        assert res.status_code == 422

    def test_get_journal_list_and_search(self, client):
        """GET /journal returns list and supports text filtering."""
        # Add distinctive entry
        tag = "rare_sighting_tag_42"
        client.post("/journal", json={"common_name": "Asian Koel", "notes": f"Note with {tag}"})

        search_res = client.get(f"/journal?query={tag}")
        assert search_res.status_code == 200
        data = search_res.json()
        assert data["count"] >= 1
        assert any(tag in (o.get("notes") or "") for o in data["observations"])


class TestTTSEndpoint:
    def test_tts_valid_query(self, client):
        """GET /tts returns 200 and streaming audio/wav bytes."""
        res = client.get("/tts?text=Oriental+Magpie+Robin+identified.")
        assert res.status_code == 200
        assert res.headers["content-type"] == "audio/wav"
        assert len(res.content) > 0
        # Check standard WAV RIFF header
        assert res.content[:4] == b"RIFF"

    def test_tts_missing_text_param(self, client):
        """GET /tts without text parameter returns 422 Unprocessable Entity."""
        res = client.get("/tts")
        assert res.status_code == 422


class TestIdentificationEndpoints:
    def test_identify_text_valid(self, client):
        """POST /identify/text processes user description and returns agent reply."""
        mock_agent_result = {
            "response": "Oriental Magpie-Robin. Check for white wing patch.",
            "tools_used": ["species_lookup"],
            "iterations": 2,
            "tool_results": [{"tool": "species_lookup", "result": {"found": True}}],
        }

        with patch("app.main.run_agent", return_value=mock_agent_result):
            res = client.post("/identify/text", json={
                "message": "I saw a small black bird with white markings",
                "lat": 15.3,
                "lon": 74.1,
            })
            assert res.status_code == 200
            data = res.json()
            assert data["response"] == mock_agent_result["response"]
            assert data["spoken_response"] != ""
            assert len(data["spoken_response"].split()) <= 25
            assert "/tts?text=" in data["tts_url"]
            assert data["tools_used"] == ["species_lookup"]

    def test_identify_text_missing_message(self, client):
        """POST /identify/text without message returns 422."""
        res = client.post("/identify/text", json={"lat": 15.3})
        assert res.status_code == 422

    def test_identify_photo_valid(self, client, sample_image_bytes):
        """POST /identify/photo uploads image, resizes, runs vision agent."""
        mock_photo_result = {
            "response": "This photo shows a Red-vented Bulbul. Note the dark crest.",
            "tools_used": ["species_lookup"],
            "iterations": 1,
            "tool_results": [],
        }

        with patch("app.main.run_photo_agent", return_value=mock_photo_result):
            files = {"file": ("test.jpg", sample_image_bytes, "image/jpeg")}
            data = {"message": "What bird is this?", "lat": "15.3", "lon": "74.1"}
            res = client.post("/identify/photo", files=files, data=data)

            assert res.status_code == 200
            body = res.json()
            assert body["response"] == mock_photo_result["response"]
            assert len(body["spoken_response"].split()) <= 25
            assert "/tts?text=" in body["tts_url"]
            assert "image_path" in body

    def test_identify_photo_empty_file(self, client):
        """POST /identify/photo with empty file returns 400 Bad Request."""
        files = {"file": ("empty.jpg", b"", "image/jpeg")}
        res = client.post("/identify/photo", files=files)
        assert res.status_code == 400
        assert "Empty image file" in res.json()["detail"]

    def test_identify_photo_missing_file(self, client):
        """POST /identify/photo without file returns 422."""
        res = client.post("/identify/photo", data={"message": "What is this?"})
        assert res.status_code == 422

    def test_identify_audio_bird_call(self, client, sample_audio_wav):
        """POST /identify/audio with nature audio triggers acoustic/BirdNET identification."""
        mock_agent_result = {
            "response": "Identified bird call as Oriental Magpie-Robin.",
            "tools_used": ["species_lookup"],
            "iterations": 1,
            "tool_results": [],
        }

        # Mock transcribe_audio to indicate NOT speech, so it takes the bird audio path
        with patch("app.main.transcribe_audio", return_value={"is_speech": False, "text": ""}), \
             patch("app.main.run_agent", return_value=mock_agent_result):

            with open(sample_audio_wav, "rb") as f:
                files = {"file": ("recording.wav", f.read(), "audio/wav")}

            res = client.post("/identify/audio", files=files)
            assert res.status_code == 200
            data = res.json()
            assert data["mode"] == "bird_audio"
            assert data["response"] == mock_agent_result["response"]
            assert "birdnet_detections" in data
            assert "/tts?text=" in data["tts_url"]

    def test_identify_audio_spoken_voice(self, client, sample_audio_wav):
        """POST /identify/audio with spoken speech triggers voice_query mode."""
        mock_agent_result = {
            "response": "You can find kingfishers near wetlands and water bodies.",
            "tools_used": ["species_lookup"],
            "iterations": 1,
            "tool_results": [],
        }

        # Mock transcribe_audio to indicate user spoke a question
        with patch("app.main.transcribe_audio", return_value={"is_speech": True, "text": "Where do I see kingfishers?"}), \
             patch("app.main.run_agent", return_value=mock_agent_result):

            with open(sample_audio_wav, "rb") as f:
                files = {"file": ("voice.wav", f.read(), "audio/wav")}

            res = client.post("/identify/audio", files=files)
            assert res.status_code == 200
            data = res.json()
            assert data["mode"] == "voice_query"
            assert data["transcription"] == "Where do I see kingfishers?"
            assert data["response"] == mock_agent_result["response"]

    def test_identify_audio_empty_file(self, client):
        """POST /identify/audio with empty file returns 400 Bad Request."""
        files = {"file": ("empty.wav", b"", "audio/wav")}
        res = client.post("/identify/audio", files=files)
        assert res.status_code == 400
        assert "Empty audio file" in res.json()["detail"]

    def test_identify_voice_dedicated_endpoint(self, client, sample_audio_wav):
        """POST /identify/voice transcribes spoken audio and returns response."""
        mock_agent_result = {
            "response": "Common Mynas often forage in pairs along grassy edges.",
            "tools_used": ["species_lookup"],
            "iterations": 1,
            "tool_results": [],
        }

        with patch("app.main.transcribe_audio", return_value={"is_speech": True, "text": "What bird walks on the lawn?"}), \
             patch("app.main.run_agent", return_value=mock_agent_result):

            with open(sample_audio_wav, "rb") as f:
                files = {"file": ("query.wav", f.read(), "audio/wav")}

            res = client.post("/identify/voice", files=files)
            assert res.status_code == 200
            data = res.json()
            assert data["transcription"] == "What bird walks on the lawn?"
            assert data["response"] == mock_agent_result["response"]
            assert "/tts?text=" in data["tts_url"]

    def test_identify_voice_empty_file(self, client):
        """POST /identify/voice with empty file returns 400 Bad Request."""
        files = {"file": ("empty.wav", b"", "audio/wav")}
        res = client.post("/identify/voice", files=files)
        assert res.status_code == 400
        assert "Empty audio file" in res.json()["detail"]


class TestMobileAppDownloadRoutes:
    def test_download_app_info(self, client):
        """GET /download/app/info returns metadata and download instructions."""
        res = client.get("/download/app/info")
        assert res.status_code == 200
        data = res.json()
        assert data["app_name"] == "Field Companion Mobile"
        assert data["version"] == "1.0.0"
        assert data["download_url"] == "/download/app"
        assert "instructions" in data

    def test_download_app_file(self, client):
        """GET /download/app returns the APK binary file with attachment disposition."""
        res = client.get("/download/app")
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/vnd.android.package-archive"
        assert "FieldCompanion.apk" in res.headers["content-disposition"]
        assert len(res.content) > 0

    def test_download_apk_alias(self, client):
        """GET /download/field-companion.apk alias returns the same APK binary."""
        res = client.get("/download/field-companion.apk")
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/vnd.android.package-archive"

    def test_download_app_redirect_when_configured(self, client, monkeypatch):
        """When MOBILE_APP_DOWNLOAD_URL is configured and no local file, it redirects."""
        monkeypatch.setenv("MOBILE_APP_PATH", "/non/existent/path/FieldCompanion.apk")
        monkeypatch.setenv("MOBILE_APP_DOWNLOAD_URL", "https://github.com/example/releases/FieldCompanion.apk")
        res = client.get("/download/app", follow_redirects=False)
        assert res.status_code == 307
        assert res.headers["location"] == "https://github.com/example/releases/FieldCompanion.apk"

    def test_model_download_custom_url_param(self, client):
        """GET /model/download/{model_id}?custom_url=... redirects to user's custom URL."""
        custom_url = "https://custom-server.com/models/my-gemma.gguf"
        res = client.get(f"/model/download/gemma4:e2b?custom_url={custom_url}", follow_redirects=False)
        assert res.status_code == 307
        assert res.headers["location"] == custom_url

    def test_model_download_env_url(self, client, monkeypatch):
        """When MODEL_DOWNLOAD_URL is configured in environment, it redirects directly."""
        env_url = "https://my-bucket.s3.amazonaws.com/gemma-model.gguf"
        monkeypatch.setenv("MODEL_DOWNLOAD_URL", env_url)
        res = client.get("/model/download/gemma4:e2b", follow_redirects=False)
        assert res.status_code == 307
        assert res.headers["location"] == env_url


