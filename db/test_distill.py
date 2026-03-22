"""Tests for SQLite to voice knowledge base distillation."""
from __future__ import annotations
import json
import pytest
from pathlib import Path
from test_ingest import research_dir, db_path


def _populated_db(research_dir, db_path):
    from ingest import ingest_all
    ingest_all(str(research_dir), str(db_path))
    return db_path


def test_distill_produces_valid_json(research_dir, db_path, tmp_path):
    _populated_db(research_dir, db_path)
    from distill import distill_knowledge_base
    output = tmp_path / "kb.json"
    distill_knowledge_base(str(db_path), str(output))
    assert output.exists()
    kb = json.loads(output.read_text())
    assert isinstance(kb, dict)


def test_distill_has_required_sections(research_dir, db_path, tmp_path):
    _populated_db(research_dir, db_path)
    from distill import distill_knowledge_base
    output = tmp_path / "kb.json"
    distill_knowledge_base(str(db_path), str(output))
    kb = json.loads(output.read_text())
    required = ["metadata", "agent_persona", "service_area",
                "brand_ownership_map", "equipment_types",
                "triage_flows", "universal_failure_patterns",
                "safety_rules", "scheduling_info"]
    for section in required:
        assert section in kb, f"Missing section: {section}"


def test_distill_scheduling_has_az_ca_split(research_dir, db_path, tmp_path):
    _populated_db(research_dir, db_path)
    from distill import distill_knowledge_base
    output = tmp_path / "kb.json"
    distill_knowledge_base(str(db_path), str(output))
    kb = json.loads(output.read_text())
    sched = kb["scheduling_info"]
    assert "availability_by_region" in sched
    assert "arizona" in sched["availability_by_region"]
    assert "southern_california" in sched["availability_by_region"]


def test_distill_includes_triage_flows(research_dir, db_path, tmp_path):
    _populated_db(research_dir, db_path)
    from distill import distill_knowledge_base
    output = tmp_path / "kb.json"
    distill_knowledge_base(str(db_path), str(output))
    kb = json.loads(output.read_text())
    assert len(kb["triage_flows"]) >= 1


def test_distill_size_within_target(research_dir, db_path, tmp_path):
    _populated_db(research_dir, db_path)
    from distill import distill_knowledge_base
    output = tmp_path / "kb.json"
    distill_knowledge_base(str(db_path), str(output))
    size_kb = output.stat().st_size / 1024
    assert size_kb > 0.5, f"KB too small: {size_kb:.1f}KB"


def test_distill_persona_has_greeting(research_dir, db_path, tmp_path):
    _populated_db(research_dir, db_path)
    from distill import distill_knowledge_base
    output = tmp_path / "kb.json"
    distill_knowledge_base(str(db_path), str(output))
    kb = json.loads(output.read_text())
    persona = kb["agent_persona"]
    assert "Fitness Repair" in persona["greeting"]
    assert "tone" in persona


def test_distill_safety_rules_present(research_dir, db_path, tmp_path):
    _populated_db(research_dir, db_path)
    from distill import distill_knowledge_base
    output = tmp_path / "kb.json"
    distill_knowledge_base(str(db_path), str(output))
    kb = json.loads(output.read_text())
    rules = kb["safety_rules"]
    assert len(rules) >= 4
    assert any("UNPLUG" in r for r in rules)
