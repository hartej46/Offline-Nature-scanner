"""
Comprehensive tests for database operations (app.db) including edge cases.
"""

import pytest
from app.db import (
    species_count,
    search_species,
    get_species_by_name,
    check_species_in_region,
    add_observation,
    get_observation,
    search_observations,
)


class TestSpeciesQueries:
    def test_species_count(self):
        """Database must contain at least 100 species as per Checkpoint 1.2."""
        count = species_count()
        assert count >= 100
        assert isinstance(count, int)

    def test_search_species_common_name(self):
        """Searching by common name should return matching records."""
        results = search_species("Bulbul", limit=10)
        assert len(results) > 0
        names = [r["common_name"].lower() for r in results]
        assert any("bulbul" in name for name in names)

    def test_search_species_scientific_name(self):
        """Searching by scientific name should return matching records."""
        results = search_species("Pycnonotus", limit=5)
        assert len(results) > 0
        assert any("pycnonotus" in r["sci_name"].lower() for r in results)

    def test_search_species_case_insensitivity(self):
        """Search should be strictly case-insensitive."""
        res_lower = search_species("drongo")
        res_upper = search_species("DRONGO")
        res_mixed = search_species("dRoNgO")
        assert len(res_lower) == len(res_upper) == len(res_mixed)
        assert len(res_lower) > 0

    def test_search_species_empty_query(self):
        """Empty query should return species up to the limit."""
        results = search_species("", limit=15)
        assert len(results) <= 15
        assert len(results) > 0

    def test_search_species_special_characters(self):
        """SQL injection characters and wildcards should not cause errors."""
        res_sql = search_species("'; DROP TABLE species; --")
        assert isinstance(res_sql, list)

        res_wildcard = search_species("%_%")
        assert isinstance(res_wildcard, list)

        res_quotes = search_species("\"'`")
        assert isinstance(res_quotes, list)

    def test_search_species_nonexistent(self):
        """Nonexistent species should return an empty list without error."""
        results = search_species("xyz_nonexistent_creature_9999")
        assert results == []

    def test_search_species_limit_edge_cases(self):
        """Limit parameter boundaries."""
        res_1 = search_species("bird", limit=1)
        assert len(res_1) <= 1

        res_0 = search_species("bird", limit=0)
        assert len(res_0) == 0

        res_large = search_species("bird", limit=500)
        assert len(res_large) <= 500

    def test_get_species_by_name_exact(self):
        """Exact match lookup returns single species record dict."""
        sp = get_species_by_name("Oriental Magpie-Robin")
        assert sp is not None
        assert sp["common_name"] == "Oriental Magpie-Robin"
        assert "Copsychus" in sp["sci_name"]

    def test_get_species_by_name_scientific(self):
        """Lookup by exact scientific name."""
        sp = get_species_by_name("Copsychus saularis")
        assert sp is not None
        assert sp["common_name"] == "Oriental Magpie-Robin"

    def test_get_species_by_name_case_insensitive(self):
        """get_species_by_name must be case-insensitive."""
        sp = get_species_by_name("oriental magpie-robin")
        assert sp is not None
        assert sp["common_name"] == "Oriental Magpie-Robin"

    def test_get_species_by_name_nonexistent(self):
        """Unknown name should return None."""
        sp = get_species_by_name("Fictional Dragon")
        assert sp is None

    def test_check_species_in_region(self):
        """check_species_in_region adds in_region boolean flag."""
        sp = check_species_in_region("Red-vented Bulbul")
        assert sp is not None
        assert "in_region" in sp
        assert sp["in_region"] is True

        unknown = check_species_in_region("Emperor Penguin")
        assert unknown is None


class TestObservationOperations:
    def test_add_and_get_observation(self):
        """Add observation and verify retrieval by ID."""
        obs_id = add_observation(
            common_name="Oriental Magpie-Robin",
            sci_name="Copsychus saularis",
            confidence=0.92,
            source="audio",
            query_text="Melodic whistling call",
            response="Confirmed via tail feathers",
            notes="Observed at dawn in garden",
            lat=15.2993,
            lon=74.1240,
        )
        assert isinstance(obs_id, int)
        assert obs_id > 0

        # Retrieve
        obs = get_observation(obs_id)
        assert obs is not None
        assert obs["id"] == obs_id
        assert obs["common_name"] == "Oriental Magpie-Robin"
        assert obs["confidence"] == 0.92
        assert obs["notes"] == "Observed at dawn in garden"
        assert obs["lat"] == 15.2993

    def test_add_observation_minimal_fields(self):
        """Adding observation with minimal/empty fields should not fail."""
        obs_id = add_observation(
            notes="Unidentified rustling in undergrowth"
        )
        assert isinstance(obs_id, int)
        assert obs_id > 0

        obs = get_observation(obs_id)
        assert obs is not None
        assert obs["notes"] == "Unidentified rustling in undergrowth"
        assert obs["common_name"] is None or obs["common_name"] == ""

    def test_get_observation_nonexistent_id(self):
        """Querying a non-existent observation ID returns None."""
        obs = get_observation(99999999)
        assert obs is None

    def test_get_observation_invalid_id(self):
        """Negative or zero ID returns None."""
        assert get_observation(-1) is None
        assert get_observation(0) is None

    def test_search_observations(self):
        """Search observations by query substring."""
        # Ensure at least one searchable entry
        unique_note = "Observed specific rare plumage pattern xyz123"
        add_observation(
            common_name="Black Drongo",
            notes=unique_note,
        )

        results = search_observations("xyz123")
        assert len(results) >= 1
        assert any(unique_note in (r.get("notes") or "") for r in results)

    def test_search_observations_empty_query(self):
        """Empty search query returns recent observations."""
        results = search_observations("", limit=10)
        assert isinstance(results, list)

    def test_search_observations_limit(self):
        """Search results respect the limit parameter."""
        results = search_observations("", limit=2)
        assert len(results) <= 2
