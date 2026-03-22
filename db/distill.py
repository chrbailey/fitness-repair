"""Distill SQLite reference DB into voice knowledge base JSON."""
from __future__ import annotations
import json
import sqlite3
from datetime import datetime
from pathlib import Path


def distill_knowledge_base(db_path: str, output_path: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    kb = {
        "metadata": _metadata(conn),
        "agent_persona": _persona(),
        "service_area": _service_area(conn),
        "brand_ownership_map": _ownership_map(conn),
        "equipment_types": _equipment_types(conn),
        "triage_flows": _triage_flows(conn),
        "universal_failure_patterns": _failure_patterns(conn),
        "safety_rules": _safety_rules(),
        "scheduling_info": _scheduling_info(),
        "common_caller_scenarios": _common_scenarios(conn),
    }

    conn.close()
    Path(output_path).write_text(json.dumps(kb, indent=2))


def _metadata(conn: sqlite3.Connection) -> dict:
    brand_count = conn.execute("SELECT COUNT(*) FROM brands").fetchone()[0]
    flow_count = conn.execute("SELECT COUNT(*) FROM triage_flows").fetchone()[0]
    equip_types = conn.execute(
        "SELECT DISTINCT equipment_type FROM failure_patterns"
    ).fetchall()
    return {
        "version": "1.0.0",
        "generated_from": "fitness-repair.db",
        "generated_at": datetime.now().isoformat(),
        "equipment_categories": len(equip_types),
        "brands_included": brand_count,
        "triage_flows": flow_count,
    }


def _persona() -> dict:
    return {
        "name": "Fitness Repair Service",
        "greeting": (
            "Thanks for calling Fitness Repair. I can help with treadmills, "
            "ellipticals, stair steppers, and other heavy fitness equipment. "
            "What's going on with your machine?"
        ),
        "tone": "Friendly, knowledgeable repair tech. Short answers. One question at a time.",
        "closing": "Offer to schedule a tech visit or summarize next steps.",
    }


def _service_area(conn: sqlite3.Connection) -> dict:
    zones = conn.execute(
        "SELECT zone_name, state, rate_type, availability FROM service_zones"
    ).fetchall()
    core = [z["zone_name"] for z in zones if z["rate_type"] == "standard"]
    extended = [z["zone_name"] for z in zones if z["rate_type"] == "trip_charge"]
    return {
        "core_zones": core,
        "extended_zones": extended,
        "qualification_flow": (
            "Ask city or zip. Core = standard rate. Extended = trip charge. "
            "Outside = politely decline with referral suggestion."
        ),
    }


def _ownership_map(conn: sqlite3.Connection) -> dict:
    parents = conn.execute(
        "SELECT DISTINCT p.name AS parent, m.name AS child "
        "FROM manufacturers m JOIN manufacturers p ON m.parent_company_id = p.id"
    ).fetchall()
    result = {}
    for row in parents:
        result.setdefault(row["parent"], []).append(row["child"])
    return result


def _equipment_types(conn: sqlite3.Connection) -> dict:
    types = conn.execute(
        "SELECT DISTINCT equipment_type FROM failure_patterns"
    ).fetchall()
    result = {}
    for t in types:
        et = t["equipment_type"]
        brands = conn.execute(
            "SELECT DISTINCT b.name FROM brands b "
            "WHERE b.equipment_types LIKE ?", (f'%"{et}"%',)
        ).fetchall()
        failures = conn.execute(
            "SELECT component_type, symptom, frequency FROM failure_patterns "
            "WHERE equipment_type = ? ORDER BY triage_priority", (et,)
        ).fetchall()
        result[et] = {
            "common_brands": [b["name"] for b in brands],
            "top_failures": [
                {"component": f["component_type"], "symptom": f["symptom"],
                 "frequency": f["frequency"]}
                for f in failures
            ],
        }
    return result


def _triage_flows(conn: sqlite3.Connection) -> dict:
    flows = conn.execute(
        "SELECT equipment_type, entry_symptom, decision_tree FROM triage_flows"
    ).fetchall()
    result = {}
    for f in flows:
        key = f"{f['equipment_type']}__{f['entry_symptom'].lower().replace(' ', '_')}"
        result[key] = json.loads(f["decision_tree"])
    return result


def _failure_patterns(conn: sqlite3.Connection) -> dict:
    patterns = conn.execute(
        "SELECT * FROM failure_patterns ORDER BY equipment_type, triage_priority"
    ).fetchall()
    result = {}
    for p in patterns:
        key = f"{p['equipment_type']}_{p['component_type']}"
        result[key] = {
            "affects": p["equipment_type"],
            "symptom": p["symptom"],
            "root_cause": p["root_cause"],
            "typical_age": f"{p['typical_age_years']} years" if p["typical_age_years"] else "varies",
            "fix_cost": p["estimated_repair_cost"],
            "diy_possible": bool(p["diy_fixable"]),
        }
    return result


def _safety_rules() -> list:
    return [
        "Burning smell or sparking: UNPLUG IMMEDIATELY, schedule tech, do not troubleshoot further",
        "Exposed wiring: UNPLUG, tech visit only",
        "Machine making grinding metal sounds: STOP USING, could cause injury",
        "Treadmill belt catching/grabbing: STOP USING, fall hazard",
        "Heavy equipment tilting or unstable: STOP USING, secure and call tech",
    ]


def _scheduling_info() -> dict:
    return {
        "phone_hours": "Monday-Friday, 8am-5pm Pacific",
        "lead_time": "Usually within 2-3 business days",
        "availability_by_region": {
            "arizona": "Monday through Friday (weekdays)",
            "southern_california": "Saturday and Sunday (weekends)",
        },
        "talk_track_az": (
            "Our tech is in the Arizona area during the week. "
            "What day works best - any weekday preference?"
        ),
        "talk_track_ca": (
            "Our tech covers Southern California on weekends. "
            "Would Saturday or Sunday work better for you?"
        ),
        "talk_track_flexible": (
            "Let me note that preference and we'll see what we can work out."
        ),
        "what_to_collect": [
            "name", "phone", "address/zip", "equipment type",
            "brand and model if known", "brief issue description",
            "preferred day/time",
        ],
        "do_not_promise": (
            "Never confirm a specific appointment. Say: "
            "'I'll pass this along and someone will confirm your appointment shortly.'"
        ),
    }


def _common_scenarios(conn: sqlite3.Connection) -> list:
    top = conn.execute(
        "SELECT equipment_type, symptom, component_type, estimated_repair_cost "
        "FROM failure_patterns WHERE frequency = 'common' "
        "ORDER BY triage_priority LIMIT 8"
    ).fetchall()
    return [
        {
            "equipment_type": r["equipment_type"],
            "symptom": r["symptom"],
            "likely_component": r["component_type"],
            "cost_range": r["estimated_repair_cost"],
        }
        for r in top
    ]


if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python distill.py <db_path> <output_json_path>")
        sys.exit(1)
    distill_knowledge_base(sys.argv[1], sys.argv[2])
    print(f"Distilled {sys.argv[1]} -> {sys.argv[2]}")
