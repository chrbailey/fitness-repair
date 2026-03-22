# Fitness Repair Voice Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a voice agent for fitness equipment repair that triages issues over the phone and collects service requests, backed by a deep research database of manufacturers, failure patterns, and parts intelligence.

**Architecture:** Multi-agent research swarm populates a SQLite reference DB. A distillation script generates an 80-120KB JSON voice knowledge base. A Retell voice agent loads the KB, triages callers, and writes structured service requests. Integrates into the existing retell-bridge at `~/.claude/ahgen/retell-bridge/`.

**Tech Stack:** Python 3.9+ (research ingestion, distillation), TypeScript (Retell bridge agent, post-call processor), SQLite, Retell.ai WebSocket protocol.

---

## File Map

### New Files — Research & Data (`/Volumes/OWC drive/Dev/fitness-repair/`)

| File | Responsibility |
|------|---------------|
| `db/schema.sql` | SQLite schema definition (9 tables) |
| `db/ingest.py` | Merges 7 research JSON files into SQLite |
| `db/distill.py` | Generates voice KB JSON from SQLite |
| `db/test_ingest.py` | Tests for ingestion pipeline |
| `db/test_distill.py` | Tests for distillation pipeline |
| `knowledge-base/knowledge-base.json` | Distilled voice KB (auto-generated, ~80-120KB) |
| `research/manufacturers.json` | Swarm output: manufacturer census |
| `research/ownership.json` | Swarm output: corporate ownership chains |
| `research/oem-supply-chain.json` | Swarm output: Chinese OEM factories |
| `research/failure-patterns.json` | Swarm output: failure patterns by equipment type |
| `research/parts-intelligence.json` | Swarm output: parts sourcing + cross-compatibility |
| `research/triage-flows.json` | Swarm output: symptom → diagnosis decision trees |
| `research/service-zones.json` | Swarm output: SoCal + AZ zip code zones |
| `zones/zip-codes.json` | Processed zip code → zone mapping |

### New Files — Retell Bridge (`~/.claude/ahgen/retell-bridge/`)

| File | Responsibility |
|------|---------------|
| `src/agents/fitness-repair.ts` | Agent config, system prompt, KB injection |
| `src/post-call/fitness-repair.ts` | Transcript extraction: equipment, brand, issue, customer, scheduling |
| `test/simulate-fitness-call.ts` | WebSocket simulation test |

### Modified Files — Retell Bridge

| File | Change |
|------|--------|
| `src/agents/index.ts` | Register fitness-repair agent in agent registry |
| `src/post-call/index.ts` | Generalize return type, register fitness-repair processor |
| `src/types.ts` | Add `FitnessRepairIntent`, fitness repair outcomes, `fitness_repair` enrichment field on `TranscriptOutput` |
| `src/transcript.ts` | Add fitness-repair branch in `writeTranscript()` |

---

## Task 1: Research Wave 1 — Manufacturer Census, Corporate Ownership, OEM Supply Chain

Three parallel research agents. These are web research tasks, not code — no TDD applies.

**Output Files:**
- `research/manufacturers.json`
- `research/ownership.json`
- `research/oem-supply-chain.json`

- [ ] **Step 1: Dispatch Manufacturer Census agent**

Prompt the agent to research every major fitness equipment manufacturer selling in the US market. Output must be a JSON array of objects with fields: `name`, `hq_country`, `website`, `status` (active/defunct/acquired), `parent_company` (if any), `product_lines` (array of equipment types), `sold_at` (retail channels), `price_tier` (budget/mid/premium/commercial), `notes`.

Equipment categories to cover: treadmills, stair steppers/StairMasters, ellipticals, exercise bikes (upright + recumbent), rowing machines, cable machines/functional trainers, smith machines/home gyms, spin bikes.

Sources: manufacturer websites, industry associations (IHRSA, NSGA), fitness equipment directories, retail listings (Amazon, Costco, Dick's, Walmart).

Target: 40-60 manufacturers minimum. Must include: Life Fitness, Precor, Cybex, Technogym, NordicTrack, ProForm, Sole, Spirit, Horizon, Matrix, Bowflex, Schwinn, Nautilus, Peloton, StairMaster, True Fitness, Star Trac, Octane, Inspire, Body-Solid, PowerBlock, Rogue, REP Fitness, Titan Fitness, Force USA, Marcy, Sunny Health, XTERRA, Gold's Gym (home), Weslo.

Save output to: `/Volumes/OWC drive/Dev/fitness-repair/research/manufacturers.json`

- [ ] **Step 2: Dispatch Corporate Ownership agent**

Prompt the agent to research corporate ownership chains and acquisition history for fitness equipment manufacturers. Output must be a JSON object with fields: `ownership_groups` (array of `{parent, subsidiaries: [{name, acquired_date, notes}]}`) and `standalone_manufacturers` (companies not owned by a conglomerate).

Key ownership groups to map:
- iFIT (NordicTrack, ProForm, Freemotion, Weider, Gold's Gym Home)
- Nautilus Inc (Bowflex, Schwinn, Nautilus brand)
- Johnson Health Tech (Matrix, Horizon, Vision)
- Dyaco (Spirit, Sole, XTERRA, residential Matrix line)
- Brunswick (Life Fitness, Cybex, Hammer Strength — note: divested?)
- Core Health & Fitness (StairMaster, Star Trac, Schwinn commercial, Nautilus commercial)
- Technogym (standalone, Italian, IPO)
- Peloton (standalone)

Sources: SEC filings, Crunchbase, press releases, Wikipedia, industry news (Club Industry, Athletic Business).

Save output to: `/Volumes/OWC drive/Dev/fitness-repair/research/ownership.json`

- [ ] **Step 3: Dispatch OEM & Supply Chain agent**

Prompt the agent to research Chinese OEM factories behind US fitness equipment brands. Output must be a JSON object with `factories` (array of `{name, location, country, components_produced, brands_supplied, alibaba_url?, notes}`) and `shared_components` (array of `{component_type, factory, brands_sharing, part_numbers?}`).

Research targets:
- Which factories make the motors (most treadmill motors come from 3-4 factories)
- Controller board manufacturers (common source of failures)
- Display/console manufacturers
- Frame fabricators
- Belt manufacturers
- Which brands are white-labels of the same factory product (e.g., budget treadmills from the same Zhejiang factory under 5 different brand names)

Sources: Alibaba factory profiles, import record patterns (search ImportGenius/Panjiva references), teardown videos on YouTube, repair technician forums, FCC filings (for electronics).

Save output to: `/Volumes/OWC drive/Dev/fitness-repair/research/oem-supply-chain.json`

- [ ] **Step 4: Verify all three output files exist and have valid JSON**

Run:
```bash
for f in manufacturers.json ownership.json oem-supply-chain.json; do
  echo "--- $f ---"
  python3 -c "import json; d=json.load(open('/Volumes/OWC drive/Dev/fitness-repair/research/$f')); print(f'Valid JSON, {len(str(d))} chars')"
done
```

- [ ] **Step 5: Commit research Wave 1 output**

```bash
cd "/Volumes/OWC drive/Dev/fitness-repair"
git add research/manufacturers.json research/ownership.json research/oem-supply-chain.json
git commit -m "research: Wave 1 — manufacturers, ownership, OEM supply chain"
```

---

## Task 2: Research Wave 2 — Failure Patterns, Parts Intelligence

Two parallel research agents. Depends on Wave 1 output for manufacturer/brand context.

**Output Files:**
- `research/failure-patterns.json`
- `research/parts-intelligence.json`

- [ ] **Step 1: Dispatch Failure Patterns agent**

Prompt the agent with the manufacturer list from Wave 1. Research the top 10 most common failure patterns per equipment category. Output must be a JSON object keyed by equipment type, each containing an array of failure objects with fields: `component_type`, `symptom` (what the customer describes), `root_cause`, `frequency` (common/occasional/rare), `typical_age_years`, `diy_fixable` (boolean), `requires_tech` (boolean), `estimated_repair_cost`, `triage_priority` (1-5, 1=check first), `affected_brands` (array), `notes`.

Equipment categories: treadmill, elliptical, stair_stepper, exercise_bike, rower, cable_machine, smith_machine, spin_bike.

Key failure areas to research per category:
- **Treadmill:** motor brushes, belt wear/slip, deck friction, controller board, incline motor, console dead, roller bearings, safety key switch, speed sensor
- **Elliptical:** stride mechanism, resistance motor, pedal bearings, console, flywheel
- **Stair stepper:** hydraulic cylinders, alternator/generator, step chain, console
- **Exercise bike:** resistance mechanism, seat post, pedal bearings, console
- **Rower:** resistance mechanism (water/air/magnetic), seat rail, handle/chain, monitor
- **Cable machine:** cable fraying, pulley bearings, weight stack pins, cable routing
- **Smith machine:** linear bearings, safety catches, cable/pulley system, weight plate pegs
- **Spin bike:** resistance pad/brake, flywheel bearing, pedal/cleat mechanism, handlebar adjustment

Sources: iFixit, Reddit (r/homegym, r/treadmills, r/pelotoncycle, r/fitness), YouTube repair channels (Treadmill Doctor, Gym Doctors), parts store bestseller lists, warranty claim pattern discussions.

CRITICAL: For treadmills, note that motor/heater replacement is the #1 MISDIAGNOSIS — always check power supply and control board FIRST. This lesson from the sauna agent applies to fitness equipment too.

Save output to: `/Volumes/OWC drive/Dev/fitness-repair/research/failure-patterns.json`

- [ ] **Step 2: Dispatch Parts Intelligence agent**

Prompt the agent with the manufacturer list from Wave 1. Research parts sourcing for each major brand and cross-compatible components. Output must be a JSON object with:
- `brand_specific_sources`: keyed by brand, array of `{supplier, url?, phone?, notes}`
- `universal_sources`: array of `{supplier, url?, phone?, component_types, notes}`
- `cross_compatible_parts`: array of `{component_type, part_description, fits_brands, fits_models?, source, price_range}`
- `proprietary_warnings`: array of `{brand, component, why_proprietary, workaround?}`

Key research targets:
- Official parts departments for each manufacturer (phone numbers, websites)
- Third-party parts retailers (Treadmill Doctor / treadmilldoctor.com, Gym Source, Amazon fitness parts sellers)
- Universal components: treadmill belts (measured by width x length), DC motors (by HP and mount type), console batteries, lubricants
- Proprietary gotchas: iFIT/NordicTrack locked consoles, Peloton proprietary everything, Technogym Unity console

Sources: manufacturer parts pages, Amazon fitness parts category, eBay, treadmilldoctor.com, gympart.com, fitnessrepairparts.com, fitnesssuperstore.com parts dept.

Save output to: `/Volumes/OWC drive/Dev/fitness-repair/research/parts-intelligence.json`

- [ ] **Step 3: Verify output files**

```bash
for f in failure-patterns.json parts-intelligence.json; do
  echo "--- $f ---"
  python3 -c "import json; d=json.load(open('/Volumes/OWC drive/Dev/fitness-repair/research/$f')); print(f'Valid JSON, {len(str(d))} chars')"
done
```

- [ ] **Step 4: Commit research Wave 2 output**

```bash
cd "/Volumes/OWC drive/Dev/fitness-repair"
git add research/failure-patterns.json research/parts-intelligence.json
git commit -m "research: Wave 2 — failure patterns and parts intelligence"
```

---

## Task 3: Research Wave 3 — Triage Flow Builder

One agent that synthesizes Wave 1 + Wave 2 into structured decision trees. Depends on both prior waves.

**Output File:** `research/triage-flows.json`

- [ ] **Step 1: Dispatch Triage Flow Builder agent**

Provide the agent with the contents of `failure-patterns.json` and `parts-intelligence.json`. Build structured triage decision trees — one per common symptom per equipment type.

Output must be a JSON object keyed by `{equipment_type}__{symptom_slug}` (e.g., `treadmill__wont_start`), each containing:
```json
{
  "equipment_type": "treadmill",
  "entry_symptom": "Treadmill won't turn on",
  "talk_track_opener": "Let's figure out what's going on with your treadmill...",
  "steps": [
    {
      "question": "Is the safety key in place and pushed all the way in?",
      "if_yes": "next",
      "if_no": "Try reinserting the safety key firmly. Universal replacements are about $8 on Amazon if yours is damaged. Want to try that first, or would you like a tech to come take a look?",
      "diy_possible": true
    }
  ],
  "resolution_needs_tech": "Sounds like it could be the motor controller or a deeper electrical issue. I'd recommend having our tech come take a look.",
  "resolution_diy": "Great — sounds like that fixed it! Call us back if you run into anything else.",
  "safety_abort": "If you see sparking or smell burning, please unplug the machine immediately. That's a safety issue that needs a professional."
}
```

Target: ~24 triage flows covering the top 3 symptoms per equipment type:
- Treadmill: won't start, belt slipping, burning smell/sparking
- Elliptical: squeaking/grinding, no resistance, console dead
- Stair stepper: won't resist, hydraulic leak, uneven steps
- Exercise bike: no resistance, seat/pedal issue, console dead
- Rower: resistance stuck, seat won't glide, monitor dead
- Cable machine: cable fraying, pulley noise, stuck weight stack
- Smith machine: bar sticking, safety catch issue, cable problem
- Spin bike: resistance knob not working, clicking/grinding, wobble

Each flow should follow this pattern:
1. Safety check first (any burning, sparking, grinding → abort)
2. Simple checks first (plugged in? safety key? power strip vs wall?)
3. Component isolation (which part is failing?)
4. DIY vs tech determination
5. If tech needed → transition to info collection

Save output to: `/Volumes/OWC drive/Dev/fitness-repair/research/triage-flows.json`

- [ ] **Step 2: Verify output**

```bash
python3 -c "
import json
d = json.load(open('/Volumes/OWC drive/Dev/fitness-repair/research/triage-flows.json'))
print(f'Triage flows: {len(d)} total')
for k in sorted(d.keys()):
    steps = len(d[k].get('steps', []))
    print(f'  {k}: {steps} steps')
"
```

Expected: ~24 flows, 3-6 steps each.

- [ ] **Step 3: Commit**

```bash
cd "/Volumes/OWC drive/Dev/fitness-repair"
git add research/triage-flows.json
git commit -m "research: Wave 3 — triage decision trees (24 flows)"
```

---

## Task 4: Research Wave 4 — Geography & Service Zones

Independent of other waves — can run in parallel with any wave.

**Output File:** `research/service-zones.json`, `zones/zip-codes.json`

- [ ] **Step 1: Dispatch Geography agent**

Research and compile service zone data for SoCal and AZ. Output must be a JSON object with:
```json
{
  "zones": [
    {
      "zone_name": "Phoenix Metro",
      "state": "AZ",
      "rate_type": "standard",
      "trip_charge_amount": null,
      "availability": "weekdays",
      "cities": ["Phoenix", "Scottsdale", "Tempe", "Mesa", "Chandler", "Gilbert", "Glendale", "Peoria", "Surprise"],
      "zip_codes": ["85001", "85002", ...]
    },
    {
      "zone_name": "Tucson Metro",
      "state": "AZ",
      "rate_type": "standard",
      "trip_charge_amount": null,
      "availability": "weekdays",
      "cities": ["Tucson", "Marana", "Oro Valley", "Sahuarita"],
      "zip_codes": [...]
    },
    {
      "zone_name": "AZ Extended",
      "state": "AZ",
      "rate_type": "trip_charge",
      "trip_charge_amount": null,
      "availability": "weekdays",
      "cities": ["Flagstaff", "Prescott", "Sedona", "Yuma", "Sierra Vista"],
      "zip_codes": [...]
    },
    {
      "zone_name": "LA Metro",
      "state": "CA",
      "rate_type": "standard",
      "trip_charge_amount": null,
      "availability": "weekends",
      "cities": ["Los Angeles", "Long Beach", "Pasadena", "Burbank", "Santa Monica", ...],
      "zip_codes": [...]
    },
    {
      "zone_name": "San Diego Metro",
      "state": "CA",
      "rate_type": "standard",
      "trip_charge_amount": null,
      "availability": "weekends",
      "cities": ["San Diego", "Chula Vista", "Oceanside", "Carlsbad", "Escondido", ...],
      "zip_codes": [...]
    },
    {
      "zone_name": "Orange County",
      "state": "CA",
      "rate_type": "standard",
      "trip_charge_amount": null,
      "availability": "weekends",
      "cities": ["Anaheim", "Irvine", "Santa Ana", "Huntington Beach", ...],
      "zip_codes": [...]
    },
    {
      "zone_name": "Inland Empire",
      "state": "CA",
      "rate_type": "standard",
      "trip_charge_amount": null,
      "availability": "weekends",
      "cities": ["Riverside", "San Bernardino", "Ontario", "Rancho Cucamonga", ...],
      "zip_codes": [...]
    },
    {
      "zone_name": "SoCal Extended",
      "state": "CA",
      "rate_type": "trip_charge",
      "trip_charge_amount": null,
      "availability": "weekends",
      "cities": ["Santa Barbara", "Ventura", "Bakersfield", "Palm Springs", ...],
      "zip_codes": [...]
    }
  ]
}
```

Sources: USPS zip code database, Census data for metro area definitions.

Save raw output to: `/Volumes/OWC drive/Dev/fitness-repair/research/service-zones.json`

- [ ] **Step 2: Generate processed zip-codes.json**

Transform the raw zones into a flat lookup: `{zip_code: {zone_name, state, rate_type, availability}}`. Save to `/Volumes/OWC drive/Dev/fitness-repair/zones/zip-codes.json`.

- [ ] **Step 3: Verify**

```bash
python3 -c "
import json
zones = json.load(open('/Volumes/OWC drive/Dev/fitness-repair/research/service-zones.json'))
zips = json.load(open('/Volumes/OWC drive/Dev/fitness-repair/zones/zip-codes.json'))
print(f'Zones: {len(zones[\"zones\"])}')
print(f'Total zip codes mapped: {len(zips)}')
for z in zones['zones']:
    print(f'  {z[\"zone_name\"]}: {len(z[\"zip_codes\"])} zips, {z[\"rate_type\"]}, {z[\"availability\"]}')
"
```

- [ ] **Step 4: Commit**

```bash
cd "/Volumes/OWC drive/Dev/fitness-repair"
git add research/service-zones.json zones/zip-codes.json
git commit -m "research: Wave 4 — service zones and zip code mapping"
```

---

## Task 5: Database Schema & Ingestion

TDD from here forward. Python 3.9+, SQLite.

**Files:**
- Create: `/Volumes/OWC drive/Dev/fitness-repair/db/schema.sql`
- Create: `/Volumes/OWC drive/Dev/fitness-repair/db/ingest.py`
- Create: `/Volumes/OWC drive/Dev/fitness-repair/db/test_ingest.py`

- [ ] **Step 1: Write schema.sql**

Create the 9-table schema from the spec. Include all tables: `manufacturers`, `brands`, `models`, `oem_factories`, `parts_catalog`, `failure_patterns`, `triage_flows`, `service_zones`, `techs`, `service_calls`. Include `CREATE INDEX` statements on foreign keys and common query columns (`equipment_type`, `brand`, `zip code lookups`).

```sql
-- /Volumes/OWC drive/Dev/fitness-repair/db/schema.sql
CREATE TABLE IF NOT EXISTS manufacturers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  hq_country TEXT,
  website TEXT,
  status TEXT NOT NULL DEFAULT 'active',
  parent_company_id INTEGER REFERENCES manufacturers(id),
  notes TEXT
);

CREATE TABLE IF NOT EXISTS brands (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  manufacturer_id INTEGER NOT NULL REFERENCES manufacturers(id),
  name TEXT NOT NULL UNIQUE,
  equipment_types TEXT,
  price_tier TEXT,
  sold_at TEXT,
  status TEXT NOT NULL DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS oem_factories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  location TEXT,
  country TEXT,
  components_produced TEXT,
  brands_supplied TEXT
);

CREATE TABLE IF NOT EXISTS models (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  brand_id INTEGER NOT NULL REFERENCES brands(id),
  name TEXT NOT NULL,
  equipment_type TEXT NOT NULL,
  years_produced_start INTEGER,
  years_produced_end INTEGER,
  motor_type TEXT,
  motor_hp REAL,
  weight_lbs REAL,
  msrp_range TEXT,
  oem_factory_id INTEGER REFERENCES oem_factories(id),
  notes TEXT
);

CREATE TABLE IF NOT EXISTS parts_catalog (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  component_type TEXT NOT NULL,
  oem_factory_id INTEGER REFERENCES oem_factories(id),
  compatible_model_ids TEXT,
  cross_compatible_part_ids TEXT,
  typical_price_range TEXT,
  sources TEXT
);

CREATE TABLE IF NOT EXISTS failure_patterns (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  equipment_type TEXT NOT NULL,
  component_type TEXT NOT NULL,
  symptom TEXT NOT NULL,
  root_cause TEXT,
  frequency TEXT,
  typical_age_years INTEGER,
  diy_fixable INTEGER DEFAULT 0,
  requires_tech INTEGER DEFAULT 1,
  estimated_repair_cost TEXT,
  triage_priority INTEGER
);

CREATE TABLE IF NOT EXISTS triage_flows (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  equipment_type TEXT NOT NULL,
  entry_symptom TEXT NOT NULL,
  decision_tree TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS service_zones (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  zone_name TEXT NOT NULL,
  state TEXT NOT NULL,
  zip_codes TEXT NOT NULL,
  rate_type TEXT NOT NULL,
  trip_charge_amount REAL,
  availability TEXT NOT NULL,
  tech_ids TEXT
);

CREATE TABLE IF NOT EXISTS techs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  phone TEXT,
  email TEXT,
  base_state TEXT,
  az_availability TEXT,
  ca_availability TEXT,
  zones TEXT,
  specialties TEXT,
  active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS service_calls (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp TEXT NOT NULL DEFAULT (datetime('now')),
  caller_phone TEXT,
  equipment_type TEXT,
  brand TEXT,
  model TEXT,
  symptom TEXT,
  triage_result TEXT,
  customer_name TEXT,
  customer_address TEXT,
  customer_zip TEXT,
  zone_id INTEGER REFERENCES service_zones(id),
  state TEXT,
  requested_days TEXT,
  requested_time_window TEXT,
  trip_charge INTEGER DEFAULT 0,
  status TEXT DEFAULT 'pending',
  notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_brands_manufacturer ON brands(manufacturer_id);
CREATE INDEX IF NOT EXISTS idx_models_brand ON models(brand_id);
CREATE INDEX IF NOT EXISTS idx_models_equipment ON models(equipment_type);
CREATE INDEX IF NOT EXISTS idx_failure_equipment ON failure_patterns(equipment_type);
CREATE INDEX IF NOT EXISTS idx_failure_component ON failure_patterns(component_type);
CREATE INDEX IF NOT EXISTS idx_service_calls_status ON service_calls(status);
CREATE INDEX IF NOT EXISTS idx_service_calls_date ON service_calls(timestamp);
```

- [ ] **Step 2: Write failing test for ingestion**

```python
# /Volumes/OWC drive/Dev/fitness-repair/db/test_ingest.py
from __future__ import annotations
import json
import os
import sqlite3
import tempfile
import pytest
from pathlib import Path

# Minimal test fixtures
SAMPLE_MANUFACTURERS = [
    {"name": "iFIT", "hq_country": "US", "website": "ifit.com", "status": "active",
     "parent_company": None, "product_lines": ["treadmill", "elliptical", "bike"],
     "sold_at": ["direct", "retail"], "price_tier": "mid", "notes": "Parent of NordicTrack, ProForm"},
    {"name": "NordicTrack", "hq_country": "US", "website": "nordictrack.com", "status": "active",
     "parent_company": "iFIT", "product_lines": ["treadmill", "elliptical", "bike"],
     "sold_at": ["Costco", "direct"], "price_tier": "mid", "notes": "Subsidiary of iFIT"}
]

SAMPLE_OWNERSHIP = {
    "ownership_groups": [
        {"parent": "iFIT", "subsidiaries": [
            {"name": "NordicTrack", "acquired_date": "1998", "notes": "flagship brand"}
        ]}
    ],
    "standalone_manufacturers": []
}

SAMPLE_OEM = {
    "factories": [
        {"name": "Shuhua Sports", "location": "Fujian", "country": "China",
         "components_produced": ["motors", "frames"], "brands_supplied": ["NordicTrack", "ProForm"]}
    ],
    "shared_components": [
        {"component_type": "motor", "factory": "Shuhua Sports",
         "brands_sharing": ["NordicTrack", "ProForm"]}
    ]
}

SAMPLE_FAILURES = {
    "treadmill": [
        {"component_type": "motor_brushes", "symptom": "Burning smell under load",
         "root_cause": "Carbon brush wear", "frequency": "common", "typical_age_years": 6,
         "diy_fixable": True, "requires_tech": False, "estimated_repair_cost": "$15-30",
         "triage_priority": 2, "affected_brands": ["NordicTrack", "ProForm"], "notes": ""}
    ]
}

SAMPLE_PARTS = {
    "brand_specific_sources": {
        "NordicTrack": [{"supplier": "iFIT Parts", "url": "ifit.com/parts", "phone": "866-896-9777", "notes": ""}]
    },
    "universal_sources": [
        {"supplier": "Treadmill Doctor", "url": "treadmilldoctor.com", "phone": "888-750-4766",
         "component_types": ["belts", "motors", "controllers", "lubricant"], "notes": "Best universal source"}
    ],
    "cross_compatible_parts": [],
    "proprietary_warnings": []
}

SAMPLE_TRIAGE = {
    "treadmill__wont_start": {
        "equipment_type": "treadmill",
        "entry_symptom": "Treadmill won't turn on",
        "talk_track_opener": "Let's figure this out...",
        "steps": [
            {"question": "Is the safety key in place?", "if_yes": "next",
             "if_no": "Try reinserting the safety key.", "diy_possible": True}
        ],
        "resolution_needs_tech": "Sounds like a tech visit is needed.",
        "resolution_diy": "Glad that fixed it!",
        "safety_abort": "Unplug immediately if you see sparking."
    }
}

SAMPLE_ZONES = {
    "zones": [
        {"zone_name": "Phoenix Metro", "state": "AZ", "rate_type": "standard",
         "trip_charge_amount": None, "availability": "weekdays",
         "cities": ["Phoenix", "Scottsdale"], "zip_codes": ["85001", "85251"]}
    ]
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
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
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


def test_ingest_is_idempotent(research_dir, db_path):
    from ingest import ingest_all
    ingest_all(str(research_dir), str(db_path))
    ingest_all(str(research_dir), str(db_path))  # run again
    conn = sqlite3.connect(str(db_path))
    count = conn.execute("SELECT COUNT(*) FROM manufacturers").fetchone()[0]
    conn.close()
    assert count == 2  # still 2, not 4
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd "/Volumes/OWC drive/Dev/fitness-repair/db" && python3 -m pytest test_ingest.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ingest'`

- [ ] **Step 4: Write ingest.py**

```python
# /Volumes/OWC drive/Dev/fitness-repair/db/ingest.py
"""Ingest research JSON files into the fitness-repair SQLite database."""
from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from typing import Optional, Union


def _read_json(path: Path) -> Union[dict, list]:
    with open(path) as f:
        return json.load(f)


def _init_schema(conn: sqlite3.Connection) -> None:
    schema_path = Path(__file__).parent / "schema.sql"
    conn.executescript(schema_path.read_text())


def _ingest_manufacturers(conn: sqlite3.Connection, data: list) -> dict[str, int]:
    """Insert manufacturers, return name->id mapping."""
    name_to_id: dict[str, int] = {}
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
                "INSERT OR IGNORE INTO brands (manufacturer_id, name, equipment_types, price_tier, sold_at, status) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (mid, m["name"], json.dumps(m.get("product_lines", [])),
                 m.get("price_tier"), json.dumps(m.get("sold_at", [])),
                 m.get("status", "active")),
            )
    return name_to_id


def _ingest_oem(conn: sqlite3.Connection, data: dict) -> None:
    for f in data.get("factories", []):
        conn.execute(
            "INSERT OR IGNORE INTO oem_factories (name, location, country, components_produced, brands_supplied) "
            "VALUES (?, ?, ?, ?, ?)",
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
                "typical_age_years, diy_fixable, requires_tech, estimated_repair_cost, triage_priority) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (equip_type, f["component_type"], f["symptom"], f.get("root_cause"),
                 f.get("frequency"), f.get("typical_age_years"),
                 1 if f.get("diy_fixable") else 0,
                 1 if f.get("requires_tech", True) else 0,
                 f.get("estimated_repair_cost"), f.get("triage_priority")),
            )


def _ingest_parts(conn: sqlite3.Connection, data: dict) -> None:
    # Brand-specific sources as parts_catalog entries
    for brand, sources in data.get("brand_specific_sources", {}).items():
        for s in sources:
            conn.execute(
                "INSERT INTO parts_catalog (name, component_type, sources) VALUES (?, ?, ?)",
                (f"{brand} parts", "brand_source", json.dumps(s)),
            )
    # Universal sources
    for s in data.get("universal_sources", []):
        conn.execute(
            "INSERT INTO parts_catalog (name, component_type, sources) VALUES (?, ?, ?)",
            (s["supplier"], "universal_source", json.dumps(s)),
        )
    # Cross-compatible parts
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
            "INSERT INTO triage_flows (equipment_type, entry_symptom, decision_tree) VALUES (?, ?, ?)",
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
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd "/Volumes/OWC drive/Dev/fitness-repair/db" && python3 -m pytest test_ingest.py -v`
Expected: All 7 tests PASS

- [ ] **Step 6: Commit**

```bash
cd "/Volumes/OWC drive/Dev/fitness-repair"
git add db/schema.sql db/ingest.py db/test_ingest.py
git commit -m "feat: database schema and research ingestion pipeline"
```

---

## Task 6: Distillation Script

Generates the 80-120KB voice knowledge base JSON from the SQLite database.

**Files:**
- Create: `/Volumes/OWC drive/Dev/fitness-repair/db/distill.py`
- Create: `/Volumes/OWC drive/Dev/fitness-repair/db/test_distill.py`
- Output: `/Volumes/OWC drive/Dev/fitness-repair/knowledge-base/knowledge-base.json`

- [ ] **Step 1: Write failing test**

```python
# /Volumes/OWC drive/Dev/fitness-repair/db/test_distill.py
from __future__ import annotations
import json
import sqlite3
import pytest
from pathlib import Path
from test_ingest import research_dir, db_path, SAMPLE_MANUFACTURERS  # reuse fixtures


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
    """With real data this should be 80-120KB. With test fixtures, just verify it's reasonable."""
    _populated_db(research_dir, db_path)
    from distill import distill_knowledge_base
    output = tmp_path / "kb.json"
    distill_knowledge_base(str(db_path), str(output))
    size_kb = output.stat().st_size / 1024
    # Test fixtures are small; just verify it's non-trivial
    assert size_kb > 0.5, f"KB too small: {size_kb:.1f}KB"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "/Volumes/OWC drive/Dev/fitness-repair/db" && python3 -m pytest test_distill.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'distill'`

- [ ] **Step 3: Write distill.py**

```python
# /Volumes/OWC drive/Dev/fitness-repair/db/distill.py
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
            "What day works best — any weekday preference?"
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
    # Build from most common failure patterns
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
    print(f"Distilled {sys.argv[1]} → {sys.argv[2]}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/Volumes/OWC drive/Dev/fitness-repair/db" && python3 -m pytest test_distill.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
cd "/Volumes/OWC drive/Dev/fitness-repair"
git add db/distill.py db/test_distill.py
git commit -m "feat: distillation script — SQLite to voice KB JSON"
```

---

## Task 7: Voice Agent Configuration

TypeScript. Integrates into the existing Retell bridge.

**Files:**
- Create: `~/.claude/ahgen/retell-bridge/src/agents/fitness-repair.ts`
- Modify: `~/.claude/ahgen/retell-bridge/src/agents/index.ts`

- [ ] **Step 1: Write fitness-repair.ts agent config**

```typescript
// ~/.claude/ahgen/retell-bridge/src/agents/fitness-repair.ts
import { readFileSync } from "fs";
import { resolve } from "path";
import type { AgentConfig } from "./index";

const KB_PATH = process.env.FITNESS_KB_PATH
  || "/Volumes/OWC drive/Dev/fitness-repair/knowledge-base/knowledge-base.json";

let knowledgeBase: string;
try {
  knowledgeBase = readFileSync(resolve(KB_PATH), "utf-8");
  console.log(`[fitness-repair] Knowledge base loaded (${(knowledgeBase.length / 1024).toFixed(0)} KB)`);
} catch (err) {
  console.error(`[fitness-repair] Failed to load knowledge base from ${KB_PATH}: ${err}`);
  knowledgeBase = "{}";
}

const SYSTEM_PROMPT = `You are the Fitness Repair service specialist — a friendly, knowledgeable voice agent handling phone calls about fitness equipment troubleshooting and service scheduling.

## Your Role
- Help callers diagnose issues with their fitness equipment (treadmills, ellipticals, stair steppers, bikes, rowers, cable machines, smith machines, spin bikes)
- Identify the equipment type, brand, model, and specific issue
- Walk them through troubleshooting steps conversationally
- Determine if the issue needs a technician or is a DIY fix
- If a tech visit is needed, collect their info and scheduling preferences
- Be honest about what you know and don't know

## Conversation Style
- Warm, patient, knowledgeable — like talking to a trusted repair technician
- Ask clarifying questions naturally: equipment type, brand, model, age, what's happening
- Keep responses SHORT for voice — 2-3 sentences max per turn
- When walking through troubleshooting, do ONE STEP at a time and wait for their response
- If you don't know something, say so and offer to have someone follow up

## Opening
When the call connects, say:
"Thanks for calling Fitness Repair. I can help with treadmills, ellipticals, stair steppers, and other heavy fitness equipment. What's going on with your machine?"

## Critical Rules

### Safety First
- Burning smell, sparking, or smoke → tell caller to UNPLUG IMMEDIATELY. Do not troubleshoot further. Schedule a tech visit.
- Grinding metal sounds → tell caller to STOP USING the machine. Could cause injury.
- Treadmill belt catching or grabbing → STOP USING. Fall hazard.
- Exposed wiring → UNPLUG, tech visit only.
- Heavy equipment tilting/unstable → STOP USING, secure it, call tech.

### Scheduling Awareness
- Arizona customers: our tech is available WEEKDAYS (Monday through Friday)
- Southern California customers: our tech is available WEEKENDS (Saturday and Sunday)
- Ask their city or zip code to determine which region they're in
- Frame availability naturally: "Our tech is in your area on [weekdays/weekends], what works best?"
- If they want a day outside the pattern, say: "Let me note that preference and we'll see what we can work out."
- NEVER promise a specific appointment. Say: "I'll pass this along and someone will confirm your appointment shortly."

### Service Area
- Core zones (standard rate): Phoenix Metro, Tucson Metro, LA Metro, San Diego Metro, Orange County, Inland Empire
- Extended zones (trip charge applies): AZ rural areas, SoCal extended (Santa Barbara, Ventura, Bakersfield, Palm Springs)
- Outside service area: politely decline, suggest they search for local repair services

### Info Collection (when tech visit is needed)
Collect ALL of these before closing:
1. Customer name
2. Phone number (confirm the number they're calling from or get a better one)
3. Address and zip code
4. Equipment type, brand, and model (if known)
5. Brief description of the issue
6. Preferred day and time window

### Troubleshooting Flow
For each issue:
1. Confirm the symptom
2. Check for safety issues first
3. Walk through diagnostic steps ONE AT A TIME
4. Wait for the caller to report back before moving to the next step
5. Determine: DIY fix or tech visit needed
6. If DIY: confirm the fix, offer to schedule anyway if they want help
7. If tech: collect their info (see above)

### Unknown Equipment
If someone calls about equipment or a brand you don't have information on:
"I don't have the specifics on that model handy. Let me get your info and have someone follow up with the details."

## Knowledge Base
The following JSON contains data on brands, common failures, triage flows, parts, and service areas. Reference it for all technical answers:

${knowledgeBase}`;

export const fitnessRepairAgent: AgentConfig = {
  name: "fitness-repair",
  model: process.env.FITNESS_LLM_MODEL || "claude-sonnet-4-6-20250514",
  maxTokens: 400,
  systemPrompt: SYSTEM_PROMPT,
  postCallHandler: "fitness-repair",
};
```

- [ ] **Step 2: Register in agents/index.ts**

Add to imports:
```typescript
import { fitnessRepairAgent } from "./fitness-repair";
```

Add to `initializeAgents()`:
```typescript
const fitnessId = process.env.RETELL_FITNESS_AGENT_ID;
if (fitnessId) registerAgent(fitnessId, fitnessRepairAgent);
if (fitnessId) console.log(`[agents] Fitness repair agent: ${fitnessId}`);
```

- [ ] **Step 3: Commit**

```bash
cd ~/.claude/ahgen/retell-bridge
git add src/agents/fitness-repair.ts src/agents/index.ts
git commit -m "feat: fitness repair voice agent config"
```

---

## Task 8: Post-Call Processor & Bridge Integration

TypeScript. Transcript extraction + types updates + transcript.ts wiring.

**Files:**
- Create: `~/.claude/ahgen/retell-bridge/src/post-call/fitness-repair.ts`
- Modify: `~/.claude/ahgen/retell-bridge/src/post-call/index.ts`
- Modify: `~/.claude/ahgen/retell-bridge/src/types.ts`
- Modify: `~/.claude/ahgen/retell-bridge/src/transcript.ts`

- [ ] **Step 1: Write fitness-repair post-call processor**

```typescript
// ~/.claude/ahgen/retell-bridge/src/post-call/fitness-repair.ts
import type { PostCallInput } from "./index";

export interface FitnessRepairPostCallResult {
  equipment_type: string;
  brand?: string;
  model?: string;
  symptom: string;
  triage_result: "diy_fix" | "needs_tech" | "safety_issue" | "unknown";
  customer: {
    name?: string;
    phone: string;
    address?: string;
    zip?: string;
  };
  scheduling: {
    requested_days: string;
    requested_time_window?: string;
    zone: string;
    trip_charge: boolean;
    state: "AZ" | "CA" | "unknown";
  };
  intents: string[];
  flags: {
    unknown_brand: boolean;
    safety_issue: boolean;
    outside_service_area: boolean;
  };
}

const EQUIPMENT_KEYWORDS: Record<string, string[]> = {
  treadmill: ["treadmill", "tread mill", "walking machine", "running machine"],
  elliptical: ["elliptical", "cross trainer", "crosstrainer"],
  stair_stepper: ["stair stepper", "stairstepper", "stairmaster", "stair master", "step machine", "stepper"],
  exercise_bike: ["exercise bike", "stationary bike", "recumbent", "upright bike"],
  rower: ["rower", "rowing machine", "row machine", "erg", "ergometer"],
  cable_machine: ["cable machine", "cable crossover", "functional trainer", "cable system", "pulley"],
  smith_machine: ["smith machine", "smith rack", "home gym", "multi gym", "multigym", "all-in-one"],
  spin_bike: ["spin bike", "spinning bike", "peloton", "indoor cycle", "cycling bike"],
};

const BRAND_KEYWORDS: Record<string, string[]> = {
  nordictrack: ["nordictrack", "nordic track"],
  proform: ["proform", "pro form"],
  sole: ["sole fitness", "sole treadmill", "sole f"],
  life_fitness: ["life fitness", "lifefitness"],
  precor: ["precor"],
  bowflex: ["bowflex", "bow flex"],
  schwinn: ["schwinn"],
  nautilus: ["nautilus"],
  horizon: ["horizon"],
  matrix: ["matrix"],
  spirit: ["spirit fitness"],
  peloton: ["peloton"],
  stairmaster: ["stairmaster", "stair master"],
  cybex: ["cybex"],
  technogym: ["technogym", "techno gym"],
  true_fitness: ["true fitness"],
  body_solid: ["body solid", "body-solid", "bodysolid"],
  rogue: ["rogue"],
  titan: ["titan fitness"],
  sunny: ["sunny health", "sunny fitness"],
  xterra: ["xterra"],
  gold_gym: ["gold's gym", "golds gym"],
  marcy: ["marcy"],
  inspire: ["inspire fitness"],
};

const SYMPTOM_KEYWORDS: Record<string, string[]> = {
  wont_start: ["won't turn on", "wont turn on", "dead", "no power", "doesn't turn on", "nothing happens", "blank"],
  no_resistance: ["no resistance", "resistance doesn't work", "too easy", "feels loose", "no tension"],
  belt_issue: ["belt slipping", "belt sliding", "belt off center", "belt worn", "belt needs"],
  noise: ["squeaking", "grinding", "clicking", "banging", "rattling", "knocking", "loud"],
  burning_smell: ["burning", "smoke", "smells hot", "electrical smell", "burning smell"],
  display_dead: ["screen blank", "display dead", "console won't", "screen not working", "no display"],
  motor_issue: ["motor", "hesitates", "surges", "speed inconsistent"],
  cable_issue: ["cable fraying", "cable snapped", "cable loose", "cable stuck"],
  leak: ["leaking", "hydraulic", "oil", "fluid"],
  wobble: ["wobble", "unstable", "shaking", "rocking", "loose"],
};

const AZ_ZIPS_PREFIX = ["85", "86"];
const CA_SOCAL_ZIPS_PREFIX = ["90", "91", "92", "93"];

const SAFETY_KEYWORDS = [
  "burning", "smoke", "sparking", "spark", "fire", "shock",
  "exposed wire", "electrical smell", "catching", "grabbing",
];

const FOLLOW_UP_TRIGGERS = [
  "schedule", "come out", "send someone", "tech", "technician",
  "fix it", "repair", "service call", "appointment",
];

function detectEquipmentType(text: string): string {
  const lower = text.toLowerCase();
  for (const [type, keywords] of Object.entries(EQUIPMENT_KEYWORDS)) {
    if (keywords.some((kw) => lower.includes(kw))) return type;
  }
  return "unknown";
}

function detectBrand(text: string): string | undefined {
  const lower = text.toLowerCase();
  for (const [brand, keywords] of Object.entries(BRAND_KEYWORDS)) {
    if (keywords.some((kw) => lower.includes(kw))) return brand;
  }
  return undefined;
}

function detectSymptoms(text: string): string[] {
  const lower = text.toLowerCase();
  const symptoms: string[] = [];
  for (const [symptom, keywords] of Object.entries(SYMPTOM_KEYWORDS)) {
    if (keywords.some((kw) => lower.includes(kw))) symptoms.push(symptom);
  }
  return symptoms.length > 0 ? symptoms : ["general_inquiry"];
}

function detectSafetyIssue(text: string): boolean {
  const lower = text.toLowerCase();
  return SAFETY_KEYWORDS.some((kw) => lower.includes(kw));
}

function detectNeedsTech(text: string): boolean {
  const lower = text.toLowerCase();
  return FOLLOW_UP_TRIGGERS.some((kw) => lower.includes(kw));
}

function detectState(text: string): "AZ" | "CA" | "unknown" {
  const lower = text.toLowerCase();
  // Look for state mentions
  if (lower.includes("arizona") || lower.includes(" az ") || lower.includes(" az,")) return "AZ";
  if (lower.includes("california") || lower.includes(" ca ") || lower.includes(" ca,")) return "CA";
  // Look for zip codes
  const zipMatch = text.match(/\b(\d{5})\b/);
  if (zipMatch) {
    const prefix = zipMatch[1].substring(0, 2);
    if (AZ_ZIPS_PREFIX.includes(prefix)) return "AZ";
    if (CA_SOCAL_ZIPS_PREFIX.includes(prefix)) return "CA";
  }
  // Look for city names
  const azCities = ["phoenix", "scottsdale", "tempe", "mesa", "chandler", "gilbert", "tucson", "flagstaff", "prescott"];
  const caCities = ["los angeles", "san diego", "irvine", "anaheim", "pasadena", "burbank", "riverside", "long beach", "oceanside"];
  if (azCities.some((c) => lower.includes(c))) return "AZ";
  if (caCities.some((c) => lower.includes(c))) return "CA";
  return "unknown";
}

function extractZip(text: string): string | undefined {
  const match = text.match(/\b(\d{5})\b/);
  return match ? match[1] : undefined;
}

export function processFitnessRepairCall(input: PostCallInput): FitnessRepairPostCallResult {
  const fullText = input.transcript.map((t) => t.content).join(" ");
  const userText = input.transcript
    .filter((t) => t.role === "user")
    .map((t) => t.content)
    .join(" ");

  const equipmentType = detectEquipmentType(fullText);
  const brand = detectBrand(fullText);
  const symptoms = detectSymptoms(userText);
  const safetyIssue = detectSafetyIssue(fullText);
  const needsTech = detectNeedsTech(fullText);
  const state = detectState(fullText);
  const zip = extractZip(fullText);

  let triageResult: FitnessRepairPostCallResult["triage_result"];
  if (safetyIssue) triageResult = "safety_issue";
  else if (needsTech) triageResult = "needs_tech";
  else if (symptoms.includes("general_inquiry")) triageResult = "unknown";
  else triageResult = "diy_fix";

  return {
    equipment_type: equipmentType,
    brand,
    symptom: symptoms.join(", "),
    triage_result: triageResult,
    customer: {
      phone: input.caller_number || "unknown",
      zip,
    },
    scheduling: {
      requested_days: state === "AZ" ? "weekday" : state === "CA" ? "weekend" : "unknown",
      zone: zip ? "lookup_needed" : "unknown",
      trip_charge: false,
      state,
    },
    intents: symptoms,
    flags: {
      unknown_brand: !brand,
      safety_issue: safetyIssue,
      outside_service_area: state === "unknown",
    },
  };
}
```

- [ ] **Step 2: Generalize post-call/index.ts return type**

Replace the entire file:

```typescript
// ~/.claude/ahgen/retell-bridge/src/post-call/index.ts
import { processSaunaServiceCall } from "./sauna-service";
import { processFitnessRepairCall } from "./fitness-repair";
import type { FitnessRepairPostCallResult } from "./fitness-repair";
import type { Utterance } from "../types";

export interface PostCallInput {
  call_id: string;
  agent_type: string;
  direction: "inbound" | "outbound";
  caller_number?: string;
  duration_seconds: number;
  transcript: Utterance[];
  metadata: Record<string, unknown>;
}

export interface SaunaPostCallResult {
  brand?: string;
  model?: string;
  issue_summary: string;
  intents: string[];
  parts_sources: Array<{ name: string; url?: string; phone?: string }>;
  follow_up_needed: boolean;
  follow_up_reason?: string;
  customer_name?: string;
  customer_phone?: string;
}

export type PostCallResult = SaunaPostCallResult | FitnessRepairPostCallResult;

const processors: Record<string, (input: PostCallInput) => PostCallResult> = {
  "sauna-service": processSaunaServiceCall,
  "fitness-repair": processFitnessRepairCall,
};

export function runPostCallProcessor(input: PostCallInput): PostCallResult | null {
  const processor = processors[input.agent_type];
  if (!processor) return null;
  return processor(input);
}
```

- [ ] **Step 3: Add fitness types to types.ts**

Add after `SaunaServiceIntent`:
```typescript
export type FitnessRepairIntent =
  | "wont_start"
  | "no_resistance"
  | "belt_issue"
  | "noise"
  | "burning_smell"
  | "display_dead"
  | "motor_issue"
  | "cable_issue"
  | "leak"
  | "wobble"
  | "general_inquiry";
```

Update `Intent` type:
```typescript
export type Intent = SalesIntent | SaunaServiceIntent | FitnessRepairIntent;
```

Add fitness outcomes to `CallOutcome`:
```typescript
  // Fitness repair outcomes
  | "tech_visit_scheduled"
  | "diy_fix_provided"
  | "safety_escalation";
```

Add `fitness_repair` field to `TranscriptOutput`:
```typescript
  fitness_repair?: {
    equipment_type: string;
    brand?: string;
    model?: string;
    symptom: string;
    triage_result: string;
    customer_zip?: string;
    state?: string;
    requested_days?: string;
    flags: {
      unknown_brand: boolean;
      safety_issue: boolean;
      outside_service_area: boolean;
    };
  };
```

- [ ] **Step 4: Wire fitness-repair into transcript.ts**

Add after the `sauna-service` branch in `writeTranscript()`:

```typescript
  } else if (agentType === "fitness-repair") {
    const result = runPostCallProcessor({
      call_id: callId,
      agent_type: agentType,
      direction,
      caller_number: callerNumber,
      duration_seconds: durationSeconds,
      transcript,
      metadata,
    });

    const fr = result as import("./post-call/fitness-repair").FitnessRepairPostCallResult | null;
    intents = (fr?.intents || ["general_inquiry"]) as Intent[];
    outcome = fr?.triage_result === "safety_issue"
      ? "safety_escalation"
      : fr?.triage_result === "needs_tech"
        ? "tech_visit_scheduled"
        : fr?.triage_result === "diy_fix"
          ? "diy_fix_provided"
          : "conversation_completed";
    fitnessRepair = fr
      ? {
          equipment_type: fr.equipment_type,
          brand: fr.brand,
          symptom: fr.symptom,
          triage_result: fr.triage_result,
          customer_zip: fr.customer.zip,
          state: fr.scheduling.state,
          requested_days: fr.scheduling.requested_days,
          flags: fr.flags,
        }
      : undefined;
```

Add `fitnessRepair` variable declaration near the top of the function:
```typescript
let fitnessRepair: TranscriptOutput["fitness_repair"];
```

Add to the `output` object:
```typescript
fitness_repair: fitnessRepair,
```

- [ ] **Step 5: Build and verify**

```bash
cd ~/.claude/ahgen/retell-bridge && npm run build
```

Expected: Build succeeds with no type errors.

- [ ] **Step 6: Commit**

```bash
cd ~/.claude/ahgen/retell-bridge
git add src/post-call/fitness-repair.ts src/post-call/index.ts src/types.ts src/transcript.ts
git commit -m "feat: fitness repair post-call processor and bridge integration"
```

---

## Task 9: Simulation Test

**Files:**
- Create: `~/.claude/ahgen/retell-bridge/test/simulate-fitness-call.ts`

- [ ] **Step 1: Write simulation test**

Model after `test/simulate-sauna-call.ts`. Simulate a treadmill repair call:
- Caller reports NordicTrack treadmill won't start
- Agent asks about safety key, power cord
- Caller says safety key is in, plugged into wall
- Agent asks about console lights — caller says no lights
- Agent determines tech visit needed
- Collects name, phone, Phoenix AZ zip code
- Agent offers weekday scheduling
- Call ends

The simulation connects via WebSocket to the local bridge and sends `response_required` messages with the caller's utterances. Verify the transcript JSON is written with correct `equipment_type`, `brand`, `triage_result`, and `scheduling.state`.

- [ ] **Step 2: Run simulation**

```bash
cd ~/.claude/ahgen/retell-bridge && npx ts-node test/simulate-fitness-call.ts
```

Verify output JSON in `~/.claude/ahgen/calls/`.

- [ ] **Step 3: Commit**

```bash
cd ~/.claude/ahgen/retell-bridge
git add test/simulate-fitness-call.ts
git commit -m "test: fitness repair call simulation"
```

---

## Task 10: Management Skill & Final Polish

**Files:**
- Create: `~/.claude/skills/fitness-repair/SKILL.md`

- [ ] **Step 1: Write Claude Code management skill**

```markdown
---
name: fitness-repair
description: Manage the Fitness Repair voice agent — review call transcripts, check service requests, enrich the knowledge base, and regenerate the voice KB.
---

# Fitness Repair Management

## Review Recent Calls

Check for new call transcripts:
\`\`\`bash
ls -lt ~/.claude/ahgen/calls/ | head -20
\`\`\`

For each fitness-repair call, read the transcript JSON and summarize:
- Equipment type, brand, model
- Issue and triage result
- Customer info and scheduling preferences
- Any flags (unknown brand, safety issue, outside area)

## Pending Service Requests

Query the database for pending service calls:
\`\`\`bash
sqlite3 "/Volumes/OWC drive/Dev/fitness-repair/db/fitness-repair.db" \
  "SELECT id, timestamp, equipment_type, brand, symptom, customer_name, customer_zip, state, requested_days, status FROM service_calls WHERE status = 'pending' ORDER BY timestamp DESC"
\`\`\`

## Enrich Database

When an unknown brand is flagged, research it and add to the database manually.

## Regenerate Voice KB

After database updates:
\`\`\`bash
cd "/Volumes/OWC drive/Dev/fitness-repair/db"
python3 distill.py "/Volumes/OWC drive/Dev/fitness-repair/db/fitness-repair.db" "/Volumes/OWC drive/Dev/fitness-repair/knowledge-base/knowledge-base.json"
\`\`\`

Then restart the Retell bridge to pick up the new KB.
```

- [ ] **Step 2: Commit skill**

```bash
git -C ~/.claude add skills/fitness-repair/SKILL.md
git -C ~/.claude commit -m "feat: fitness repair Claude Code management skill"
```

- [ ] **Step 3: Push everything to GitHub**

```bash
cd "/Volumes/OWC drive/Dev/fitness-repair"
git push origin main
```

- [ ] **Step 4: Final verification checklist**

- [ ] All research JSON files present in `research/`
- [ ] Database schema creates cleanly: `sqlite3 :memory: < db/schema.sql`
- [ ] Ingest tests pass: `cd db && python3 -m pytest test_ingest.py -v`
- [ ] Distill tests pass: `cd db && python3 -m pytest test_distill.py -v`
- [ ] Bridge builds: `cd ~/.claude/ahgen/retell-bridge && npm run build`
- [ ] Simulation test runs successfully
- [ ] KB JSON exists and is 80-120KB (with real data)
- [ ] GitHub repo is current: `git log --oneline -5`
