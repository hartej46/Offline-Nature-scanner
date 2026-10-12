"""
Comprehensive tests for agent logic, prompt rules, and tool orchestration (app.agent).
Covers: SYSTEM_PROMPT rules (safety, grounding, 25-word limit), run_agent loop,
tool execution inside loop, iteration limits, error handling, multimodal payloads.
"""

import json
import pytest
from unittest.mock import patch, MagicMock

from app.agent import (
    SYSTEM_PROMPT,
    MAX_ITERATIONS,
    run_agent,
    run_photo_agent,
)


def _make_mock_response(content: str = None, tool_calls: list = None):
    """Helper to mock an OpenAI chat completion response."""
    choice = MagicMock()
    choice.message.content = content
    choice.message.tool_calls = tool_calls or []
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _make_tool_call(call_id: str, fn_name: str, fn_args: dict):
    """Helper to mock an OpenAI tool call object."""
    tc = MagicMock()
    tc.id = call_id
    tc.function.name = fn_name
    tc.function.arguments = json.dumps(fn_args)
    return tc


class TestSystemPromptRules:
    def test_system_prompt_grounding_rule(self):
        """Rule 1: Grounding species against local checklist tools."""
        assert "GROUNDING" in SYSTEM_PROMPT
        assert "species_lookup" in SYSTEM_PROMPT
        assert "checklist_check" in SYSTEM_PROMPT

    def test_system_prompt_safety_warning_mandatory(self):
        """Rule 6: Mandatory plant/fungi safety warning."""
        assert "SAFETY" in SYSTEM_PROMPT
        assert "Do not eat or touch any plant or fungus based on this identification." in SYSTEM_PROMPT

    def test_system_prompt_conciseness_rule(self):
        """Rule 4: Spoken replies strictly under 25 words."""
        assert "CONCISENESS" in SYSTEM_PROMPT
        assert "25 words" in SYSTEM_PROMPT

    def test_system_prompt_look_back_at_nature(self):
        """Rule 5: Always suggest something to look for or listen to in the real world."""
        assert "LOOK BACK AT NATURE" in SYSTEM_PROMPT


class TestAgentLoop:
    def test_run_agent_direct_response(self):
        """LLM responds directly without calling any tools."""
        mock_resp = _make_mock_response(
            content="I can help you identify birds, plants, and other nature sightings."
        )

        with patch("app.agent.chat", return_value=mock_resp):
            result = run_agent("Hello! What can you do?")

            assert result["response"] == "I can help you identify birds, plants, and other nature sightings."
            assert result["tools_used"] == []
            assert result["iterations"] == 1
            assert result["tool_results"] == []

    def test_run_agent_single_tool_call(self):
        """Agent executes tool call and returns LLM's final response after seeing result."""
        # Step 1: Model requests species_lookup
        tc = _make_tool_call("call_001", "species_lookup", {"name": "Oriental Magpie-Robin"})
        step1_resp = _make_mock_response(content=None, tool_calls=[tc])

        # Step 2: Model gives final answer
        step2_resp = _make_mock_response(
            content="Most likely Oriental Magpie-Robin. Check for white wing patches."
        )

        with patch("app.agent.chat", side_effect=[step1_resp, step2_resp]) as mock_chat:
            result = run_agent("I saw a black and white robin")

            assert "Oriental Magpie-Robin" in result["response"]
            assert result["tools_used"] == ["species_lookup"]
            assert result["iterations"] == 2
            assert len(result["tool_results"]) == 1
            assert result["tool_results"][0]["tool"] == "species_lookup"
            assert result["tool_results"][0]["result"]["found"] is True

            # Verify chat was called twice
            assert mock_chat.call_count == 2

    def test_run_agent_multiple_tools_in_one_step(self):
        """Model requests two tools in parallel in a single step."""
        tc1 = _make_tool_call("call_a", "species_lookup", {"name": "Asian Koel"})
        tc2 = _make_tool_call("call_b", "checklist_check", {"name": "Asian Koel", "month": 5})
        step1_resp = _make_mock_response(content=None, tool_calls=[tc1, tc2])
        step2_resp = _make_mock_response(content="Asian Koel confirmed in the region.")

        with patch("app.agent.chat", side_effect=[step1_resp, step2_resp]):
            result = run_agent("What is making a loud koo-OO sound?")

            assert result["tools_used"] == ["species_lookup", "checklist_check"]
            assert len(result["tool_results"]) == 2
            assert result["iterations"] == 2

    def test_run_agent_max_iterations_exceeded(self):
        """Agent must terminate cleanly when hitting MAX_ITERATIONS without infinite looping."""
        tc = _make_tool_call("call_loop", "species_lookup", {"name": "Black Drongo"})
        looping_resp = _make_mock_response(content=None, tool_calls=[tc])

        with patch("app.agent.chat", return_value=looping_resp):
            result = run_agent("Tell me about this bird")

            assert result["iterations"] == MAX_ITERATIONS
            assert "not able to complete" in result["response"]
            assert len(result["tools_used"]) == MAX_ITERATIONS

    def test_run_agent_llm_exception_handling(self):
        """LLM failure raises exception handled gracefully without server crash."""
        with patch("app.agent.chat", side_effect=RuntimeError("Connection refused by Ollama")):
            result = run_agent("Hello")

            assert "Something went wrong" in result["response"]
            assert "error" in result
            assert "Connection refused" in result["error"]

    def test_run_agent_with_extra_context(self):
        """Extra context (classifier hints, GPS location) is passed into the user prompt."""
        mock_resp = _make_mock_response(content="Noted location.")

        with patch("app.agent.chat", return_value=mock_resp) as mock_chat:
            run_agent(
                user_message="Identify this bird",
                extra_context="Lat: 15.3, Lon: 74.1, Audio Peak: 3800 Hz",
            )

            call_args = mock_chat.call_args[1]
            user_msg = call_args["messages"][-1]
            assert "Identify this bird" in user_msg["content"]
            assert "Lat: 15.3" in user_msg["content"]

    def test_run_agent_with_conversation_history(self):
        """Conversation history messages are preserved in the message stack."""
        history = [
            {"role": "user", "content": "Prior message 1"},
            {"role": "assistant", "content": "Prior response 1"},
        ]
        mock_resp = _make_mock_response(content="New response.")

        with patch("app.agent.chat", return_value=mock_resp) as mock_chat:
            run_agent("Next message", conversation_history=history)

            messages = mock_chat.call_args[1]["messages"]
            assert messages[1] == history[0]
            assert messages[2] == history[1]
            assert messages[3]["content"] == "Next message"

    def test_run_agent_multimodal_payload_format(self):
        """Passing image_base64 packages OpenAI multimodal format with data URI."""
        fake_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
        mock_resp = _make_mock_response(content="Identified bird in image.")

        with patch("app.agent.chat", return_value=mock_resp) as mock_chat:
            run_agent(
                user_message="What bird is in this photo?",
                image_base64=fake_b64,
            )

            messages = mock_chat.call_args[1]["messages"]
            user_content = messages[-1]["content"]
            assert isinstance(user_content, list)
            assert user_content[0]["type"] == "text"
            assert user_content[1]["type"] == "image_url"
            assert f"data:image/jpeg;base64,{fake_b64}" in user_content[1]["image_url"]["url"]

    def test_run_photo_agent_custom_prompt(self):
        """run_photo_agent injects photo identification guidelines and safety disclaimer."""
        fake_b64 = "sample_photo_bytes_base64"
        mock_resp = _make_mock_response(content="Identified flower.")

        with patch("app.agent.chat", return_value=mock_resp) as mock_chat:
            run_photo_agent(
                image_base64=fake_b64,
                user_message="Identify this mushroom",
                checklist_context="Local checklist has 5 fungus species",
            )

            messages = mock_chat.call_args[1]["messages"]
            system_msg = messages[0]["content"]
            assert "PHOTO IDENTIFICATION RULES" in system_msg
            assert "never state it is safe to touch or eat" in system_msg
            assert "Local checklist has 5 fungus species" in system_msg
