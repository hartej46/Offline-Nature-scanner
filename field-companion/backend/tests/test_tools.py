"""
Comprehensive tests for agent tools (app.tools) and tool execution.
Covers: species_lookup, checklist_check, journal_add, journal_search, execute_tool, and tool definitions.
Includes edge cases: empty strings, unknown tools, invalid args, non-existent entries.
"""

import json
import pytest
from app.tools import (
    species_lookup,
    checklist_check,
    journal_add,
    journal_search,
    execute_tool,
    TOOL_DEFINITIONS,
    TOOL_FUNCTIONS,
)


class TestToolDefinitions:
    def test_tool_definitions_structure(self):
        """All tools in TOOL_DEFINITIONS must have valid OpenAI function format."""
        assert len(TOOL_DEFINITIONS) >= 4
        tool_names = set()
        for t in TOOL_DEFINITIONS:
            assert t["type"] == "function"
            fn = t["function"]
            assert "name" in fn
            assert "description" in fn
            assert "parameters" in fn
            assert fn["parameters"]["type"] == "object"
            assert "properties" in fn["parameters"]
            tool_names.add(fn["name"])

        expected_tools = {"species_lookup", "checklist_check", "journal_add", "journal_search"}
        assert expected_tools.issubset(tool_names)

    def test_tool_functions_registry(self):
        """All defined tools must have a corresponding callable in TOOL_FUNCTIONS."""
        for t in TOOL_DEFINITIONS:
            name = t["function"]["name"]
            assert name in TOOL_FUNCTIONS
            assert callable(TOOL_FUNCTIONS[name])


class TestSpeciesLookup:
    def test_species_lookup_exact_common_name(self):
        """Exact common name match returns found=True and species details."""
        res = species_lookup("Oriental Magpie-Robin")
        assert res["found"] is True
        assert res["common_name"] == "Oriental Magpie-Robin"
        assert "sci_name" in res
        assert "in_region" in res

    def test_species_lookup_exact_scientific_name(self):
        """Exact scientific name match returns found=True."""
        res = species_lookup("Copsychus saularis")
        assert res["found"] is True
        assert res["common_name"] == "Oriental Magpie-Robin"

    def test_species_lookup_case_insensitive(self):
        """Lookup must work regardless of letter casing."""
        res = species_lookup("blACk DrOnGo")
        assert res["found"] is True
        assert res["common_name"] == "Black Drongo"

    def test_species_lookup_fuzzy_search(self):
        """Partial query returns candidates list when no exact match."""
        res = species_lookup("Bulbul")
        assert res["found"] is True
        if "candidates" in res:
            assert len(res["candidates"]) > 0
            assert all("common_name" in c for c in res["candidates"])
        else:
            # Exact match if single Bulbul entry
            assert "common_name" in res

    def test_species_lookup_nonexistent(self):
        """Non-existent species returns found=False with informative message."""
        res = species_lookup("Mythical Gryphon")
        assert res["found"] is False
        assert "no species matching" in res["message"].lower()

    def test_species_lookup_empty_query(self):
        """Empty string query should not crash."""
        res = species_lookup("")
        assert isinstance(res, dict)
        assert "found" in res

    def test_species_lookup_special_characters(self):
        """Special characters, quotes, and punctuation should not crash."""
        res = species_lookup("!@#$%^&*()_+-=")
        assert isinstance(res, dict)
        assert res["found"] is False


class TestChecklistCheck:
    def test_checklist_check_valid_species(self):
        """Species in the regional checklist returns found=True."""
        res = checklist_check("Red-vented Bulbul")
        assert res["found"] is True
        assert res["common_name"] == "Red-vented Bulbul"
        assert res["in_region"] is True
        assert "warning" not in res

    def test_checklist_check_with_explicit_month(self):
        """Passing an explicit month (1-12) succeeds."""
        res = checklist_check("Oriental Magpie-Robin", month=6)
        assert res["found"] is True
        assert res["month_checked"] == 6

    def test_checklist_check_default_month(self):
        """Default month should be current calendar month (1-12)."""
        res = checklist_check("Common Myna")
        assert res["found"] is True
        assert 1 <= res["month_checked"] <= 12

    def test_checklist_check_unknown_species(self):
        """Species not in checklist returns found=False with warning message."""
        res = checklist_check("Polar Bear")
        assert res["found"] is False
        assert "message" in res
        assert "not in the local checklist" in res["message"]

    def test_checklist_check_empty_name(self):
        """Empty string returns found=False."""
        res = checklist_check("")
        assert res["found"] is False


class TestJournalAdd:
    def test_journal_add_full_record(self):
        """Add observation with all fields populated."""
        res = journal_add(
            common_name="Spotted Dove",
            sci_name="Spilopelia chinensis",
            confidence=0.88,
            source="photo",
            notes="Perched on fence post",
            query_text="What dove is this?",
            response_text="Spotted Dove based on collar pattern",
            lat=15.3,
            lon=74.1,
            audio_path="/data/audio.wav",
            image_path="/data/photo.jpg",
        )
        assert res["saved"] is True
        assert isinstance(res["observation_id"], int)
        assert "Spotted Dove" in res["message"]

    def test_journal_add_minimal(self):
        """Add observation with only common_name provided."""
        res = journal_add(common_name="Asian Koel")
        assert res["saved"] is True
        assert isinstance(res["observation_id"], int)

    def test_journal_add_none_values(self):
        """Optional parameters as None should succeed cleanly."""
        res = journal_add(
            common_name="Greater Coucal",
            sci_name=None,
            confidence=None,
            notes=None,
        )
        assert res["saved"] is True
        assert res["observation_id"] > 0


class TestJournalSearch:
    def test_journal_search_all_recent(self):
        """journal_search without query returns recent entries."""
        res = journal_search()
        assert "count" in res
        assert "observations" in res
        assert isinstance(res["observations"], list)

    def test_journal_search_specific_query(self):
        """journal_search with specific query finds matching entries."""
        unique_mark = "unique_marker_98765"
        journal_add(common_name="Crimson Sunbird", notes=f"Found near flower {unique_mark}")

        res = journal_search(query=unique_mark)
        assert res["count"] >= 1
        assert any(unique_mark in (obs.get("notes") or "") for obs in res["observations"])

    def test_journal_search_no_match(self):
        """Query with no matches returns count=0 and empty list."""
        res = journal_search(query="completely_unmatched_term_00000")
        assert res["count"] == 0
        assert res["observations"] == []


class TestExecuteToolDispatcher:
    def test_execute_valid_species_lookup(self):
        """execute_tool with valid tool returns valid JSON string."""
        raw = execute_tool("species_lookup", {"name": "Asian Koel"})
        data = json.loads(raw)
        assert data["found"] is True

    def test_execute_valid_checklist_check(self):
        """execute_tool with checklist_check returns valid JSON string."""
        raw = execute_tool("checklist_check", {"name": "Black Drongo", "month": 5})
        data = json.loads(raw)
        assert data["found"] is True
        assert data["month_checked"] == 5

    def test_execute_valid_journal_add(self):
        """execute_tool with journal_add returns saved confirmation."""
        raw = execute_tool("journal_add", {"common_name": "Common Tailorbird", "confidence": 0.85})
        data = json.loads(raw)
        assert data["saved"] is True

    def test_execute_valid_journal_search(self):
        """execute_tool with journal_search returns count and list."""
        raw = execute_tool("journal_search", {"query": ""})
        data = json.loads(raw)
        assert "count" in data

    def test_execute_unknown_tool(self):
        """Unknown tool name returns JSON error message."""
        raw = execute_tool("nonexistent_tool_123", {"arg": "val"})
        data = json.loads(raw)
        assert "error" in data
        assert "Unknown tool" in data["error"]

    def test_execute_tool_missing_required_args(self):
        """Tool call with missing required arguments handles failure gracefully."""
        # species_lookup requires 'name'
        raw = execute_tool("species_lookup", {})
        data = json.loads(raw)
        assert "error" in data or data.get("found") is False

    def test_execute_tool_extra_unexpected_args(self):
        """Tool call with unexpected arguments should return error JSON, not crash."""
        raw = execute_tool("species_lookup", {"name": "Asian Koel", "unexpected_arg_xyz": 123})
        data = json.loads(raw)
        assert "error" in data
