"""
Comprehensive tests for audio handling and speech pipelines (app.audio).
Covers: condense_for_speech, fallback_acoustic_analysis, analyze_bird_audio,
synthesize_speech, transcribe_audio, save_audio.
Includes edge cases: silent audio, stereo audio, audio >30s, long texts with markdown,
corrupt audio files, Whisper cleaning, fallback WAV creation.
"""

import os
import io
import pytest
import numpy as np
import soundfile as sf
from unittest.mock import patch, MagicMock

from app.audio import (
    condense_for_speech,
    fallback_acoustic_analysis,
    analyze_bird_audio,
    synthesize_speech,
    transcribe_audio,
    save_audio,
    AUDIO_MAX_DURATION,
    REGIONAL_BIRD_ACOUSTIC_PROFILES,
)


class TestCondenseForSpeech:
    def test_empty_string(self):
        """Empty or whitespace input returns empty string."""
        assert condense_for_speech("") == ""
        assert condense_for_speech("   \n\t  ") == ""

    def test_short_text_unchanged(self):
        """Short sentence under 25 words is preserved."""
        text = "This is an Oriental Magpie-Robin perched on a branch."
        result = condense_for_speech(text, max_words=25)
        assert result == text
        assert len(result.split()) <= 25

    def test_long_text_truncated_to_under_25_words(self):
        """Per Checkpoint 2.2: text must be kept under 25 words."""
        long_text = (
            "The Oriental Magpie-Robin is a distinctive black and white bird with a long tail "
            "that is held upright as it hops along the ground searching for insects. It has a beautiful "
            "melodic whistle at dawn and dusk across gardens and open woodlands."
        )
        result = condense_for_speech(long_text, max_words=25)
        words = result.split()
        assert len(words) <= 25

    def test_markdown_and_formatting_stripped(self):
        """Markdown headers, bold, italics, code marks, and links are stripped."""
        md_text = (
            "### Candidate: **Red-vented Bulbul** [Pycnonotus cafer]\n"
            "Look for the *dark crest* and `red vent` under the tail."
        )
        result = condense_for_speech(md_text, max_words=25)
        assert "#" not in result
        assert "**" not in result
        assert "*" not in result
        assert "`" not in result
        assert "[" not in result
        assert "]" not in result
        assert "Red-vented Bulbul" in result

    def test_sentence_boundary_preservation(self):
        """Preserves clean sentence boundaries when possible."""
        text = "This is a Black Drongo. Check its deeply forked tail. It perches out in the open."
        result = condense_for_speech(text, max_words=15)
        words = result.split()
        assert len(words) <= 15
        assert result.endswith(".")

    def test_single_giant_sentence_truncated_with_period(self):
        """A single sentence with >25 words is sliced and ended cleanly."""
        giant_sentence = " ".join([f"word{i}" for i in range(40)])
        result = condense_for_speech(giant_sentence, max_words=25)
        assert len(result.split()) == 25
        assert result.endswith(".")


class TestAcousticAnalysis:
    def test_regional_profiles_count(self):
        """All 10 regional bird profiles must be present."""
        assert len(REGIONAL_BIRD_ACOUSTIC_PROFILES) == 10
        for p in REGIONAL_BIRD_ACOUSTIC_PROFILES:
            assert "common_name" in p
            assert "sci_name" in p
            assert "peak_freq" in p
            assert "centroid" in p
            assert "freq_range" in p

    def test_fallback_acoustic_analysis_benchmark_file(self):
        """Test on actual benchmark file: oriental_magpie_robin.wav."""
        audio_path = os.path.join(
            os.path.dirname(__file__), "..", "eval", "audio", "oriental_magpie_robin.wav"
        )
        if os.path.exists(audio_path):
            detections = fallback_acoustic_analysis(audio_path, min_confidence=0.1)
            assert len(detections) > 0
            candidate_names = [d["common_name"] for d in detections]
            assert "Oriental Magpie-Robin" in candidate_names
            assert detections[0]["common_name"] == "Oriental Magpie-Robin"
            assert detections[0]["confidence"] > 0.5
            assert "fallback - lower confidence" in detections[0]["source"]

    def test_fallback_acoustic_analysis_sine_tone_matching(self, tmp_path):
        """Synthesized 510 Hz tone should match Greater Coucal as top candidate."""
        path = str(tmp_path / "coucal_tone.wav")
        sr = 22050
        t = np.linspace(0, 1.0, sr, endpoint=False)
        tone = 0.6 * np.sin(2 * np.pi * 510 * t)
        sf.write(path, tone, sr, subtype="PCM_16")

        detections = fallback_acoustic_analysis(path, min_confidence=0.1)
        assert len(detections) > 0
        assert detections[0]["common_name"] == "Greater Coucal"

    def test_silent_audio_returns_empty(self, silent_audio_wav):
        """Silent audio returns empty list without error."""
        detections = fallback_acoustic_analysis(silent_audio_wav)
        assert detections == []

    def test_stereo_audio_handled(self, tmp_path):
        """Stereo audio (2 channels) is converted to mono and classified cleanly."""
        path = str(tmp_path / "stereo_audio.wav")
        sr = 22050
        t = np.linspace(0, 1.0, sr, endpoint=False)
        tone = 0.5 * np.sin(2 * np.pi * 1810 * t)  # 1810 Hz = Asian Koel
        stereo = np.column_stack([tone, tone])
        sf.write(path, stereo, sr, subtype="PCM_16")

        detections = fallback_acoustic_analysis(path, min_confidence=0.1)
        assert len(detections) > 0
        assert detections[0]["common_name"] == "Asian Koel"

    def test_audio_longer_than_30s_clamped(self, tmp_path):
        """Audio exceeding 30s is clamped to AUDIO_MAX_DURATION without error."""
        path = str(tmp_path / "long_audio.wav")
        sr = 16000
        # 35 seconds of 770 Hz (Spotted Dove)
        t = np.linspace(0, 35.0, int(sr * 35), endpoint=False)
        tone = 0.4 * np.sin(2 * np.pi * 770 * t)
        sf.write(path, tone, sr, subtype="PCM_16")

        detections = fallback_acoustic_analysis(path, min_confidence=0.1)
        assert len(detections) > 0
        assert detections[0]["common_name"] == "Spotted Dove"

    def test_corrupted_or_missing_audio_file(self):
        """Missing or corrupted audio path returns empty list safely."""
        detections = fallback_acoustic_analysis("/nonexistent/file.wav")
        assert detections == []

    def test_analyze_bird_audio_clamped_week(self, sample_audio_wav):
        """analyze_bird_audio handles week > 48 by clamping."""
        res = analyze_bird_audio(sample_audio_wav, week=52)
        assert isinstance(res, list)


class TestTTSAndSpeech:
    def test_synthesize_speech_creates_wav(self, tmp_path):
        """synthesize_speech creates a valid readable WAV file."""
        out_wav = str(tmp_path / "test_speech.wav")
        generated_path = synthesize_speech(
            "This is a test of the speech system.",
            output_path=out_wav,
        )
        assert os.path.exists(generated_path)
        assert os.path.getsize(generated_path) > 0

        # Verify it can be read by soundfile
        data, sr = sf.read(generated_path)
        assert sr == 22050
        assert len(data) > 0

    def test_synthesize_speech_empty_text_default(self, tmp_path):
        """Empty text synthesizes default 'Identification complete.' message."""
        out_wav = str(tmp_path / "empty_speech.wav")
        generated_path = synthesize_speech("", output_path=out_wav)
        assert os.path.exists(generated_path)
        data, _ = sf.read(generated_path)
        assert len(data) > 0

    def test_synthesize_speech_failure_fallback(self, tmp_path):
        """When macOS say command fails, synthesize_speech creates fallback WAV."""
        out_wav = str(tmp_path / "fallback.wav")
        with patch("subprocess.run", side_effect=Exception("Say binary missing")):
            generated_path = synthesize_speech("Test fallback", output_path=out_wav)
            assert os.path.exists(generated_path)
            data, sr = sf.read(generated_path)
            assert sr == 22050
            assert len(data) > 0

    def test_save_audio(self, tmp_path):
        """save_audio creates directory and writes raw bytes."""
        save_dir = str(tmp_path / "recordings")
        raw_bytes = b"RIFF_FAKE_AUDIO_BYTES_12345"
        path = save_audio(raw_bytes, save_dir, "rec.wav")
        assert os.path.exists(path)
        with open(path, "rb") as f:
            assert f.read() == raw_bytes


class TestTranscribeAudio:
    def test_transcribe_audio_silence(self, silent_audio_wav):
        """Transcribing silent audio should return is_speech=False."""
        res = transcribe_audio(silent_audio_wav)
        assert isinstance(res, dict)
        assert "text" in res
        assert "is_speech" in res
        # Pure silence shouldn't be valid conversational speech
        assert res["is_speech"] is False

    def test_transcribe_audio_cleaning_and_intent(self, tmp_path):
        """Mock Whisper output to test bracket stripping and query intent detection."""
        fake_wav = str(tmp_path / "fake.wav")
        sf.write(fake_wav, np.zeros(1000), 16000, subtype="PCM_16")

        mock_model = MagicMock()
        mock_model.transcribe.return_value = {
            "text": "[Music] What bird is this? (background noise)",
            "language": "en",
        }

        with patch("app.audio.get_whisper_model", return_value=mock_model):
            res = transcribe_audio(fake_wav)
            assert res["is_speech"] is True
            assert res["text"] == "What bird is this?"
            assert "[Music]" not in res["text"]
            assert "(background noise)" not in res["text"]

    def test_transcribe_audio_exception_handling(self):
        """Exception during transcription returns safe fallback dictionary."""
        mock_model = MagicMock()
        mock_model.transcribe.side_effect = RuntimeError("Model forward failed")

        with patch("app.audio.get_whisper_model", return_value=mock_model):
            res = transcribe_audio("/some/path.wav")
            assert res["text"] == ""
            assert res["is_speech"] is False
            assert res["language"] == "en"
