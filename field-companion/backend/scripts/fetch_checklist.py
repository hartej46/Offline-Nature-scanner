#!/usr/bin/env python3
"""
Fetch a regional species checklist from the GBIF API and populate the local SQLite DB.

Usage:
    python scripts/fetch_checklist.py

Environment variables:
    REGION_BBOX  - Bounding box: min_lat,min_lon,max_lat,max_lon
                   Default: 6.5,68.1,35.7,97.4 (India)
    DB_PATH      - Path to SQLite database
"""

import os
import sys
import time

import requests
from dotenv import load_dotenv

# Add parent directory to path so we can import app.db
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.db import init_db, bulk_insert_species, species_count

load_dotenv()

GBIF_API = "https://api.gbif.org/v1"
REGION_BBOX = os.getenv("REGION_BBOX", "6.5,68.1,35.7,97.4")

# Taxon group mapping (GBIF higher taxon keys)
# These are well-known GBIF backbone keys for major groups
TAXON_GROUPS = {
    "bird": {"class_key": 212},       # Aves
    "mammal": {"class_key": 359},     # Mammalia
    "plant": {"kingdom_key": 6},      # Plantae
    "insect": {"class_key": 216},     # Insecta
    "reptile": {"class_key": 358},    # Reptilia
    "amphibian": {"class_key": 131},  # Amphibia
    "fungi": {"kingdom_key": 5},      # Fungi
}


def parse_bbox(bbox_str: str) -> dict:
    """Parse bounding box string into GBIF-compatible geometry filter."""
    parts = [float(x.strip()) for x in bbox_str.split(",")]
    if len(parts) != 4:
        raise ValueError(f"REGION_BBOX must have 4 values, got {len(parts)}: {bbox_str}")
    min_lat, min_lon, max_lat, max_lon = parts
    return {
        "decimalLatitude": f"{min_lat},{max_lat}",
        "decimalLongitude": f"{min_lon},{max_lon}",
    }


def fetch_species_for_group(group_name: str, group_config: dict, geo_filter: dict,
                            limit_per_group: int = 300) -> list[dict]:
    """Fetch species occurrences from GBIF for a taxonomic group within a region."""
    print(f"  Fetching {group_name}...")

    params = {
        "limit": 300,
        "offset": 0,
        "facet": "speciesKey",
        "facetLimit": limit_per_group,
        **geo_filter,
    }

    # Add taxon filter
    if "class_key" in group_config:
        params["classKey"] = group_config["class_key"]
    elif "kingdom_key" in group_config:
        params["kingdomKey"] = group_config["kingdom_key"]

    try:
        resp = requests.get(
            f"{GBIF_API}/occurrence/search",
            params=params,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        print(f"    ⚠ Failed to fetch {group_name}: {e}")
        return []

    # Extract unique species from facets
    species_keys = []
    for facet in data.get("facets", []):
        if facet.get("field") == "SPECIES_KEY":
            for count_entry in facet.get("counts", []):
                species_keys.append(int(count_entry["name"]))

    if not species_keys:
        # Fallback: extract from results directly
        seen = set()
        for result in data.get("results", []):
            key = result.get("speciesKey")
            if key and key not in seen:
                species_keys.append(key)
                seen.add(key)

    # Fetch species details
    species_list = []
    for key in species_keys[:limit_per_group]:
        try:
            sp_resp = requests.get(f"{GBIF_API}/species/{key}", timeout=10)
            sp_resp.raise_for_status()
            sp_data = sp_resp.json()

            common_name = sp_data.get("vernacularName") or sp_data.get("canonicalName", "Unknown")
            sci_name = sp_data.get("canonicalName") or sp_data.get("scientificName", "Unknown")

            species_list.append({
                "common_name": common_name,
                "sci_name": sci_name,
                "taxon_group": group_name,
                "region_flag": 1,
                "notes": None,
                "gbif_key": key,
            })
        except requests.RequestException:
            continue

        # Be polite to the API
        if len(species_list) % 50 == 0:
            time.sleep(0.5)

    print(f"    Found {len(species_list)} species")
    return species_list


def fetch_all_species() -> list[dict]:
    """Fetch species for all taxonomic groups in the configured region."""
    geo_filter = parse_bbox(REGION_BBOX)
    print(f"Region bbox: {REGION_BBOX}")
    print(f"Geo filter: {geo_filter}\n")

    all_species = []
    for group_name, group_config in TAXON_GROUPS.items():
        species = fetch_species_for_group(group_name, group_config, geo_filter)
        all_species.extend(species)
        time.sleep(1)  # Rate limit between groups

    return all_species


def main():
    print("=" * 60)
    print("Field Companion — Regional Species Checklist Fetcher")
    print("=" * 60)
    print()

    # Initialize database
    init_db()
    existing = species_count()
    print(f"Existing species in DB: {existing}")

    if existing > 0:
        response = input(f"DB already has {existing} species. Re-fetch? (y/N): ").strip().lower()
        if response != "y":
            print("Skipping fetch. Done.")
            return

    # Fetch species
    print("\nFetching species from GBIF...\n")
    species_list = fetch_all_species()

    if not species_list:
        print("\n⚠ No species fetched. Check your internet connection and REGION_BBOX.")
        return

    # Insert into database
    print(f"\nInserting {len(species_list)} species into database...")
    bulk_insert_species(species_list)

    total = species_count()
    print(f"\n✅ Done! Total species in database: {total}")

    if total < 100:
        print("⚠ Warning: fewer than 100 species. Consider expanding the region or checking the API.")
    else:
        print("✅ Checkpoint 1.2 requirement met: at least 100 species in DB.")


if __name__ == "__main__":
    main()
