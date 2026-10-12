"""
Agent tools for Field Companion.
Each tool is a callable that returns structured data for the agent to reason over.
Tools: species_lookup, checklist_check, journal_add, journal_search.
"""

import json
from datetime import datetime
from typing import Optional

from app.db import (
    search_species,
    get_species_by_name,
    check_species_in_region,
    add_observation,
    search_observations,
)


# ---------------------------------------------------------------------------
# Tool definitions (OpenAI function-calling format)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "species_lookup",
            "description": (
                "Look up candidate species by common name, scientific name, or keyword in the local regional checklist. "
                "Returns species info if found, including whether it is expected in the region. "
                "Always call this to verify candidate species before proposing them to the user."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Candidate species name or search term to check in the checklist.",
                    },
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "checklist_check",
            "description": (
                "Check if a species is expected in the current region and season. "
                "Use this to verify whether a candidate identification makes sense geographically."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Common name or scientific name of the species.",
                    },
                    "month": {
                        "type": "integer",
                        "description": "Current month (1-12) to check seasonal presence.",
                    },
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "journal_add",
            "description": (
                "Save an observation to the trail journal. "
                "Use after the user confirms a species identification."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "common_name": {
                        "type": "string",
                        "description": "Common name of the observed species.",
                    },
                    "sci_name": {
                        "type": "string",
                        "description": "Scientific name of the observed species.",
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Confidence score from 0.0 to 1.0.",
                    },
                    "source": {
                        "type": "string",
                        "enum": ["audio", "photo", "text"],
                        "description": "How the species was identified.",
                    },
                    "notes": {
                        "type": "string",
                        "description": "Any user notes or field observations.",
                    },
                },
                "required": ["common_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "journal_search",
            "description": (
                "Search the trail journal for past observations. "
                "Returns recent sightings matching the query."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search term (species name, notes, etc.). Leave empty for recent entries.",
                    },
                },
                "required": [],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def species_lookup(name: str) -> dict:
    """Look up a species in the local checklist."""
    # Try exact match first
    species = get_species_by_name(name)
    if species:
        return {
            "found": True,
            "common_name": species["common_name"],
            "sci_name": species["sci_name"],
            "taxon_group": species.get("taxon_group"),
            "in_region": bool(species.get("region_flag", 0)),
            "notes": species.get("notes"),
        }

    # Try fuzzy search
    results = search_species(name, limit=5)
    if results:
        return {
            "found": True,
            "exact_match": False,
            "candidates": [
                {
                    "common_name": r["common_name"],
                    "sci_name": r["sci_name"],
                    "taxon_group": r.get("taxon_group"),
                    "in_region": bool(r.get("region_flag", 0)),
                }
                for r in results
            ],
        }

    return {"found": False, "message": f"No species matching '{name}' found in the local checklist."}


def checklist_check(name: str, month: int = None) -> dict:
    """Check if a species is expected in the region (and optionally the season)."""
    if month is None:
        month = datetime.now().month

    species = check_species_in_region(name)
    if not species:
        return {
            "found": False,
            "message": f"'{name}' is not in the local checklist. It may be misidentified or a rare visitor.",
        }

    result = {
        "found": True,
        "common_name": species["common_name"],
        "sci_name": species["sci_name"],
        "in_region": species.get("in_region", False),
        "month_checked": month,
    }

    if not result["in_region"]:
        result["warning"] = f"'{species['common_name']}' is not typically found in this region."

    return result


def journal_add(
    common_name: str,
    sci_name: str = None,
    confidence: float = None,
    source: str = None,
    notes: str = None,
    query_text: str = None,
    response_text: str = None,
    lat: float = None,
    lon: float = None,
    audio_path: str = None,
    image_path: str = None,
) -> dict:
    """Save an observation to the journal."""
    obs_id = add_observation(
        common_name=common_name,
        sci_name=sci_name,
        confidence=confidence,
        source=source,
        query_text=query_text,
        response=response_text,
        notes=notes,
        lat=lat,
        lon=lon,
        audio_path=audio_path,
        image_path=image_path,
    )
    return {
        "saved": True,
        "observation_id": obs_id,
        "message": f"Saved observation of {common_name} to your trail journal.",
    }


def journal_search(query: str = None) -> dict:
    """Search the observation journal."""
    results = search_observations(query, limit=20)
    return {
        "count": len(results),
        "observations": [
            {
                "id": r["id"],
                "timestamp": r["ts"],
                "common_name": r.get("common_name"),
                "sci_name": r.get("sci_name"),
                "confidence": r.get("confidence"),
                "source": r.get("source"),
                "notes": r.get("notes"),
            }
            for r in results
        ],
    }


# ---------------------------------------------------------------------------
# Tool dispatcher
# ---------------------------------------------------------------------------

TOOL_FUNCTIONS = {
    "species_lookup": species_lookup,
    "checklist_check": checklist_check,
    "journal_add": journal_add,
    "journal_search": journal_search,
}


def execute_tool(name: str, arguments: dict) -> str:
    """Execute a tool by name with the given arguments. Returns JSON string."""
    func = TOOL_FUNCTIONS.get(name)
    if not func:
        return json.dumps({"error": f"Unknown tool: {name}"})

    try:
        result = func(**arguments)
        return json.dumps(result)
    except Exception as e:
        return json.dumps({"error": f"Tool '{name}' failed: {str(e)}"})
