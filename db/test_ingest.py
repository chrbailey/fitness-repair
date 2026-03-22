"""Tests for research JSON ingestion into SQLite."""
from __future__ import annotations
import json
import sqlite3
import pytest
from pathlib import Path

# Minimal test fixtures
SAMPLE_MANUFACTURERS = [
    {"name": "iFIT", "hq_country": "US", "website": "ifit.com", "status": "active",
     "parent_company": None, "product_lines": ["treadmill", "elliptical", "bike"],
     "sold_at": ["direct", "retail"], "price_tier": "mid", "notes": "Parent of NordicTrack, ProForm"},
    {"name": "NordicTrack", "hq_country": "US", "website": "nordictrack.com", "status": "active",
     "parent_company": "iFIT", "product_lines": ["treadmill", "elliptical", "bike"],
     "sold_at": ["Costco", "direct"], "price_tier": "mid", "notes": "Subsidiary of iFIT"},
]

SAMPLE_OWNERSHIP = {
    "ownership_groups": [
        {"parent": "iFIT", "subsidiaries": [
            {"name": "NordicTrack", "acquired_date": "1998", "notes": "flagship brand"}
        ]}
    ],
    "standalone_manufacturers": [],
}

SAMPLE_OEM = {
    "factories": [
        {"name": "Shuhua Sports", "location": "Fujian", "country": "China",
         "components_produced": ["motors", "frames"], "brands_supplied": ["NordicTrack", "ProForm"]},
    ],
    "shared_components": [
        {"component_type": "motor", "factory": "Shuhua Sports",
         "brands_sharing": ["NordicTrack", "ProForm"]},
    ],
}

SAMPLE_FAILURES = {
    "treadmill": [
        {"component_type": "motor_brushes", "symptom": "Burning smell under load",
         "root_cause": "Carbon brush wear", "frequency": "common", "typical_age_years": 6,
         "diy_fixable": True, "requires_tech": False, "estimated_repair_cost": "$15-30",
         "triage_priority": 2, "affected_brands": ["NordicTrack", "ProForm"], "notes": ""},
    ],
}

SAMPLE_PARTS = {
    "brand_specific_sources": {
        "NordicTrack": [{"supplier": "iFIT Parts", "url": "ifit.com/parts", "phone": "866-896-9777", "notes": ""}],
    },
    "universal_sources": [
        {"supplier": "Treadmill Doctor", "url": "treadmilldoctor.com", "phone": "888-750-4766",
         "component_types": ["belts", "motors", "controllers", "lubricant"], "notes": "Best universal source"},
    ],
    "cross_compatible_parts": [],
    "proprietary_warnings": [],
}

SAMPLE_TRIAGE = {
    "treadmill__wont_start": {
        "equipment_type": "treadmill",
        "entry_symptom": "Treadmill won't turn on",
        "talk_track_opener": "Let's figure this out...",
        "steps": [
            {"question": "Is the safety key in place?", "if_yes": "next",
             "if_no": "Try reinserting the safety key.", "diy_possible": True},
        ],
        "resolution_needs_tech": "Sounds like a tech visit is needed.",
        "resolution_diy": "Glad that fixed it!",
        "safety_abort": "Unplug immediately if you see sparking.",
    },
}

SAMPLE_ZONES = {
    "zones": [
        {"zone_name": "Phoenix Metro", "state": "AZ", "rate_type": "standard",
         "trip_charge_amount": None, "availability": "weekdays",
         "cities": ["Phoenix", "Scottsdale"], "zip_codes": ["85001", "85251"]},
    ],
}


@pytest.fixture
def research_dir(tmp_path):
    """Write sample research files to a temp directory."""
    rdir = tmp_path / "research"
    rdir.mkdir()
    (rdir / "manufacturers.json").write_text(json.dumps(SAMPLE_MANUFACTURERS))
    (rdir / "ownership.json").write_text(json.dumps(SAMPLE_OWNERSHIP))
    (rdir / "oem-supply-chain.json").write_text(json.dumps(SAMPLE_OEM))
    (rdir / "failure-patterns.json").write_text(json.dumps(SAMPLE_FAILURES))
    (rdir / "parts-intelligence.json").write_text(json.dumps(SAMPLE_PARTS))
    (rdir / "triage-flows.json").write_text(json.dumps(SAMPLE_TRIAGE))
    (rdir / "service-zones.json").write_text(json.dumps(SAMPLE_ZONES))
    return rdir


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test-fitness.db"


def test_ingest_creates_all_tables(research_dir, db_path):
    from ingest import ingest_all
    ingest_all(str(research_dir), str(db_path))
    conn = sqlite3.connect(str(db_path))
    tables = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()]
    conn.close()
    expected = ["brands", "failure_patterns", "manufacturers", "models",
                "oem_factories", "parts_catalog", "service_calls",
                "service_zones", "techs", "triage_flows"]
    assert tables == expected


def test_ingest_manufacturers(research_dir, db_path):
    from ingest import ingest_all
    ingest_all(str(research_dir), str(db_path))
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute("SELECT name, status FROM manufacturers ORDER BY name").fetchall()
    conn.close()
    names = [r[0] for r in rows]
    assert "iFIT" in names
    assert "NordicTrack" in names


def test_ingest_ownership_links(research_dir, db_path):
    from ingest import ingest_all
    ingest_all(str(research_dir), str(db_path))
    conn = sqlite3.connect(str(db_path))
    row = conn.execute(
        "SELECT m.name, p.name FROM manufacturers m "
        "JOIN manufacturers p ON m.parent_company_id = p.id "
        "WHERE m.name = 'NordicTrack'"
    ).fetchone()
    conn.close()
    assert row is not None
    assert row[1] == "iFIT"


def test_ingest_failure_patterns(research_dir, db_path):
    from ingest import ingest_all
    ingest_all(str(research_dir), str(db_path))
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute(
        "SELECT equipment_type, symptom FROM failure_patterns"
    ).fetchall()
    conn.close()
    assert len(rows) >= 1
    assert rows[0][0] == "treadmill"


def test_ingest_triage_flows(research_dir, db_path):
    from ingest import ingest_all
    ingest_all(str(research_dir), str(db_path))
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute(
        "SELECT equipment_type, entry_symptom, decision_tree FROM triage_flows"
    ).fetchall()
    conn.close()
    assert len(rows) >= 1
    tree = json.loads(rows[0][2])
    assert "steps" in tree


def test_ingest_service_zones(research_dir, db_path):
    from ingest import ingest_all
    ingest_all(str(research_dir), str(db_path))
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute(
        "SELECT zone_name, state, availability FROM service_zones"
    ).fetchall()
    conn.close()
    assert len(rows) >= 1
    assert rows[0][2] == "weekdays"


def test_ingest_oem_factories(research_dir, db_path):
    from ingest import ingest_all
    ingest_all(str(research_dir), str(db_path))
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute("SELECT name, country FROM oem_factories").fetchall()
    conn.close()
    assert len(rows) >= 1
    assert rows[0][0] == "Shuhua Sports"


def test_ingest_parts_catalog(research_dir, db_path):
    from ingest import ingest_all
    ingest_all(str(research_dir), str(db_path))
    conn = sqlite3.connect(str(db_path))
    rows = conn.execute("SELECT name, component_type FROM parts_catalog").fetchall()
    conn.close()
    assert len(rows) >= 2  # brand-specific + universal


def test_ingest_is_idempotent(research_dir, db_path):
    from ingest import ingest_all
    ingest_all(str(research_dir), str(db_path))
    ingest_all(str(research_dir), str(db_path))  # run again
    conn = sqlite3.connect(str(db_path))
    count = conn.execute("SELECT COUNT(*) FROM manufacturers").fetchone()[0]
    conn.close()
    assert count == 2  # still 2, not 4
