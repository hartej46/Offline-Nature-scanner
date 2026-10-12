"""
Database schema and helpers for Field Companion.
Tables: species, observations.
"""

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "./data/field_companion.db")


def get_db_path() -> str:
    """Return the resolved database path, creating parent dirs if needed."""
    path = os.path.abspath(DB_PATH)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


@contextmanager
def get_connection():
    """Context manager for SQLite connections with WAL mode."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create tables if they don't exist."""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS species (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                common_name TEXT NOT NULL,
                sci_name    TEXT NOT NULL,
                taxon_group TEXT,          -- 'bird', 'plant', 'insect', 'mammal', etc.
                region_flag INTEGER DEFAULT 1,  -- 1 = expected in region
                notes       TEXT,
                gbif_key    INTEGER,       -- GBIF species key for cross-reference
                UNIQUE(sci_name)
            );

            CREATE TABLE IF NOT EXISTS observations (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ts          TEXT NOT NULL DEFAULT (datetime('now')),
                lat         REAL,
                lon         REAL,
                species_id  INTEGER REFERENCES species(id),
                common_name TEXT,          -- denormalized for quick display
                sci_name    TEXT,          -- denormalized
                confidence  REAL,          -- 0.0 to 1.0
                source      TEXT,          -- 'audio', 'photo', 'text'
                query_text  TEXT,          -- what the user asked
                response    TEXT,          -- what the agent said
                notes       TEXT,
                audio_path  TEXT,
                image_path  TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_species_common
                ON species(common_name COLLATE NOCASE);
            CREATE INDEX IF NOT EXISTS idx_species_sci
                ON species(sci_name COLLATE NOCASE);
            CREATE INDEX IF NOT EXISTS idx_species_group
                ON species(taxon_group);
            CREATE INDEX IF NOT EXISTS idx_obs_ts
                ON observations(ts DESC);
            CREATE INDEX IF NOT EXISTS idx_obs_species
                ON observations(species_id);
        """)


# ---------------------------------------------------------------------------
# Species helpers
# ---------------------------------------------------------------------------

def species_count() -> int:
    """Return total number of species in the database."""
    with get_connection() as conn:
        row = conn.execute("SELECT COUNT(*) FROM species").fetchone()
        return row[0]


def search_species(query: str, limit: int = 20) -> list[dict]:
    """Search species by common name or scientific name (case-insensitive)."""
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, common_name, sci_name, taxon_group, region_flag, notes
            FROM species
            WHERE common_name LIKE ? OR sci_name LIKE ?
            ORDER BY common_name
            LIMIT ?
            """,
            (f"%{query}%", f"%{query}%", limit),
        ).fetchall()
        return [dict(r) for r in rows]


def get_species_by_name(name: str) -> Optional[dict]:
    """Exact or close match lookup by common or scientific name."""
    if not name or not name.strip():
        return None
    with get_connection() as conn:
        # Try exact match first
        row = conn.execute(
            """
            SELECT id, common_name, sci_name, taxon_group, region_flag, notes
            FROM species
            WHERE common_name = ? COLLATE NOCASE OR sci_name = ? COLLATE NOCASE
            """,
            (name, name),
        ).fetchone()
        if row:
            return dict(row)
        # Fallback to LIKE
        row = conn.execute(
            """
            SELECT id, common_name, sci_name, taxon_group, region_flag, notes
            FROM species
            WHERE common_name LIKE ? OR sci_name LIKE ?
            ORDER BY common_name
            LIMIT 1
            """,
            (f"%{name}%", f"%{name}%"),
        ).fetchone()
        return dict(row) if row else None


def check_species_in_region(name: str) -> Optional[dict]:
    """Check if a species is expected in the configured region."""
    species = get_species_by_name(name)
    if species:
        species["in_region"] = bool(species.get("region_flag", 0))
    return species


def insert_species(common_name: str, sci_name: str, taxon_group: str = None,
                   region_flag: int = 1, notes: str = None, gbif_key: int = None):
    """Insert a species, ignoring duplicates."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO species (common_name, sci_name, taxon_group, region_flag, notes, gbif_key)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (common_name, sci_name, taxon_group, region_flag, notes, gbif_key),
        )


def bulk_insert_species(species_list: list[dict]):
    """Bulk insert species records. Each dict needs: common_name, sci_name, taxon_group."""
    with get_connection() as conn:
        conn.executemany(
            """
            INSERT OR IGNORE INTO species (common_name, sci_name, taxon_group, region_flag, notes, gbif_key)
            VALUES (:common_name, :sci_name, :taxon_group, :region_flag, :notes, :gbif_key)
            """,
            species_list,
        )


# ---------------------------------------------------------------------------
# Observation helpers
# ---------------------------------------------------------------------------

def add_observation(
    common_name: str = None,
    sci_name: str = None,
    confidence: float = None,
    source: str = None,
    query_text: str = None,
    response: str = None,
    notes: str = None,
    lat: float = None,
    lon: float = None,
    audio_path: str = None,
    image_path: str = None,
) -> int:
    """Add an observation to the journal. Returns the observation ID."""
    # Try to link to species table
    species_id = None
    if sci_name or common_name:
        species = get_species_by_name(sci_name or common_name)
        if species:
            species_id = species["id"]
            if not common_name:
                common_name = species["common_name"]
            if not sci_name:
                sci_name = species["sci_name"]

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO observations
                (lat, lon, species_id, common_name, sci_name, confidence, source,
                 query_text, response, notes, audio_path, image_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (lat, lon, species_id, common_name, sci_name, confidence, source,
             query_text, response, notes, audio_path, image_path),
        )
        return cursor.lastrowid


def search_observations(query: str = None, limit: int = 50) -> list[dict]:
    """Search the observation journal."""
    with get_connection() as conn:
        if query:
            rows = conn.execute(
                """
                SELECT id, ts, common_name, sci_name, confidence, source, notes, query_text
                FROM observations
                WHERE common_name LIKE ? OR sci_name LIKE ? OR notes LIKE ? OR query_text LIKE ?
                ORDER BY ts DESC
                LIMIT ?
                """,
                (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%", limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, ts, common_name, sci_name, confidence, source, notes, query_text
                FROM observations
                ORDER BY ts DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]


def get_observation(obs_id: int) -> Optional[dict]:
    """Get a single observation by ID."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM observations WHERE id = ?", (obs_id,)
        ).fetchone()
        return dict(row) if row else None


if __name__ == "__main__":
    """Quick self-test."""
    init_db()
    print(f"Database initialized at: {get_db_path()}")
    print(f"Species count: {species_count()}")
