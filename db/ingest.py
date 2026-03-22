"""Ingest research JSON files into the fitness-repair SQLite database."""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Union


def _read_json(path: Path) -> Union[dict, list]:
    with open(path) as f:
        return json.load(f)


def _init_schema(conn: sqlite3.Connection) -> None:
    schema_path = Path(__file__).parent / "schema.sql"
    conn.executescript(schema_path.read_text())


def _ingest_manufacturers(conn: sqlite3.Connection, data: list) -> Dict[str, int]:
    """Insert manufacturers, return name->id mapping."""
    name_to_id: Dict[str, int] = {}
    # First pass: insert all (without parent links)
    for m in data:
        conn.execute(
            "INSERT OR IGNORE INTO manufacturers (name, hq_country, website, status, notes) "
            "VALUES (?, ?, ?, ?, ?)",
            (m["name"], m.get("hq_country"), m.get("website"),
             m.get("status", "active"), m.get("notes")),
        )
    # Build name->id map
    for row in conn.execute("SELECT id, name FROM manufacturers"):
        name_to_id[row[1]] = row[0]
    # Second pass: link parent companies
    for m in data:
        parent = m.get("parent_company")
        if parent and parent in name_to_id:
            conn.execute(
                "UPDATE manufacturers SET parent_company_id = ? WHERE name = ?",
                (name_to_id[parent], m["name"]),
            )
    # Also create brand entries for each manufacturer's product lines
    for m in data:
        mid = name_to_id.get(m["name"])
        if mid:
            conn.execute(
                "INSERT OR IGNORE INTO brands (manufacturer_id, name, equipment_types, "
                "price_tier, sold_at, status) VALUES (?, ?, ?, ?, ?, ?)",
                (mid, m["name"], json.dumps(m.get("product_lines", [])),
                 m.get("price_tier"), json.dumps(m.get("sold_at", [])),
                 m.get("status", "active")),
            )
    return name_to_id


def _ingest_oem(conn: sqlite3.Connection, data: dict) -> None:
    for f in data.get("factories", []):
        conn.execute(
            "INSERT OR IGNORE INTO oem_factories (name, location, country, "
            "components_produced, brands_supplied) VALUES (?, ?, ?, ?, ?)",
            (f["name"], f.get("location"), f.get("country"),
             json.dumps(f.get("components_produced", [])),
             json.dumps(f.get("brands_supplied", []))),
        )


def _ingest_failures(conn: sqlite3.Connection, data: dict) -> None:
    for equip_type, failures in data.items():
        for f in failures:
            conn.execute(
                "INSERT INTO failure_patterns "
                "(equipment_type, component_type, symptom, root_cause, frequency, "
                "typical_age_years, diy_fixable, requires_tech, estimated_repair_cost, "
                "triage_priority) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (equip_type, f["component_type"], f["symptom"], f.get("root_cause"),
                 f.get("frequency"), f.get("typical_age_years"),
                 1 if f.get("diy_fixable") else 0,
                 1 if f.get("requires_tech", True) else 0,
                 f.get("estimated_repair_cost"), f.get("triage_priority")),
            )


def _ingest_parts(conn: sqlite3.Connection, data: dict) -> None:
    for brand, sources in data.get("brand_specific_sources", {}).items():
        for s in sources:
            conn.execute(
                "INSERT INTO parts_catalog (name, component_type, sources) VALUES (?, ?, ?)",
                (f"{brand} parts", "brand_source", json.dumps(s)),
            )
    for s in data.get("universal_sources", []):
        conn.execute(
            "INSERT INTO parts_catalog (name, component_type, sources) VALUES (?, ?, ?)",
            (s["supplier"], "universal_source", json.dumps(s)),
        )
    for p in data.get("cross_compatible_parts", []):
        conn.execute(
            "INSERT INTO parts_catalog (name, component_type, compatible_model_ids, sources) "
            "VALUES (?, ?, ?, ?)",
            (p.get("part_description", "unknown"), p["component_type"],
             json.dumps(p.get("fits_brands", [])),
             json.dumps({"source": p.get("source"), "price_range": p.get("price_range")})),
        )


def _ingest_triage(conn: sqlite3.Connection, data: dict) -> None:
    for key, flow in data.items():
        conn.execute(
            "INSERT INTO triage_flows (equipment_type, entry_symptom, decision_tree) "
            "VALUES (?, ?, ?)",
            (flow["equipment_type"], flow["entry_symptom"], json.dumps(flow)),
        )


def _ingest_zones(conn: sqlite3.Connection, data: dict) -> None:
    for z in data.get("zones", []):
        conn.execute(
            "INSERT INTO service_zones (zone_name, state, zip_codes, rate_type, "
            "trip_charge_amount, availability) VALUES (?, ?, ?, ?, ?, ?)",
            (z["zone_name"], z["state"], json.dumps(z["zip_codes"]),
             z["rate_type"], z.get("trip_charge_amount"), z["availability"]),
        )


def ingest_all(research_dir: str, db_path: str) -> None:
    """Ingest all research JSON files into the SQLite database.

    Idempotent: drops and recreates tables on each run.
    """
    rdir = Path(research_dir)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")

    # Drop all tables for idempotent re-ingestion
    for table in ["service_calls", "triage_flows", "failure_patterns",
                  "parts_catalog", "models", "brands", "oem_factories",
                  "service_zones", "techs", "manufacturers"]:
        conn.execute(f"DROP TABLE IF EXISTS {table}")

    _init_schema(conn)

    _ingest_manufacturers(conn, _read_json(rdir / "manufacturers.json"))
    _ingest_oem(conn, _read_json(rdir / "oem-supply-chain.json"))
    _ingest_failures(conn, _read_json(rdir / "failure-patterns.json"))
    _ingest_parts(conn, _read_json(rdir / "parts-intelligence.json"))
    _ingest_triage(conn, _read_json(rdir / "triage-flows.json"))
    _ingest_zones(conn, _read_json(rdir / "service-zones.json"))

    conn.commit()
    conn.close()


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python ingest.py <research_dir> <db_path>")
        sys.exit(1)
    ingest_all(sys.argv[1], sys.argv[2])
    print(f"Ingested research from {sys.argv[1]} into {sys.argv[2]}")
