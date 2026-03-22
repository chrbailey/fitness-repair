# Fitness Repair Voice Agent — Design Spec

**Date:** 2026-03-21
**Status:** Draft
**Brand:** Fitness Repair DBA
**Architecture:** Tiered — SQLite reference DB + distilled voice KB + Retell voice agent

---

## Overview

An AI voice agent for a fitness equipment repair service covering Southern California and Arizona. The system handles inbound and outbound phone calls, triages equipment issues, and collects service request details for manual scheduling by the tech. A multi-agent research swarm builds a comprehensive knowledge base of manufacturers, corporate ownership chains, OEM supply chains, failure patterns, and parts intelligence.

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Entity | Standalone business, separate from Coastal Saunas | New brand, new phone number, reuses Retell bridge |
| Service tech | One tech, already in place | Based in AZ, travels to SoCal on weekends |
| Knowledge architecture | Tiered (SQLite + distilled JSON) | Fat KB too large for fitness; RAG too slow for voice |
| Parts fulfillment | Tech's responsibility | Agent collects info, tech sources parts |
| Scheduling | Manual — tech reviews service requests | No calendar automation; agent collects customer info and preferences |
| Availability | AZ = weekdays, SoCal = weekends | Agent must be aware of this when discussing timing |
| Call volume | 5-15 calls/day, M-F 8-5 Pacific | Low volume to start |
| Service area | Zip-based with flex | Core zones = standard rate; extended = trip charge |

---

## 1. Research Swarm Architecture

Seven specialized agents run in parallel waves to build comprehensive fitness equipment intelligence.

### Agent Roster

| Agent | Mission | Sources |
|-------|---------|---------|
| Manufacturer Census | Every commercial/residential fitness equipment manufacturer selling in the US. Name, HQ, status (active/defunct/acquired), product lines | Web search, manufacturer directories, industry associations (IHRSA, NSGA) |
| Corporate Ownership | Who owns who. Acquisition history, parent companies, subsidiary chains | SEC filings, press releases, Wikipedia, Crunchbase |
| OEM & Supply Chain | Chinese factories behind the brands. Which brands share motors, controllers, frames | Alibaba factory profiles, import records, teardown reports, repair forums |
| Failure Patterns | Top 10 failures per equipment category. What breaks, why, how often, typical age at failure | Repair forums (iFixit, Reddit r/homegym, r/treadmills), YouTube repair channels, parts store bestsellers |
| Parts Intelligence | Who sells parts for each manufacturer. Cross-compatible parts. Universal vs proprietary components | Parts retailers, Amazon/eBay listings, manufacturer parts departments |
| Triage Flow Builder | Structured symptom-to-diagnosis-to-resolution decision trees per equipment type | Synthesizes outputs from Failure Patterns + Parts Intelligence agents |
| Geography & Dispatch | SoCal and AZ zip code coverage map. Drive time zones. Standard rate vs trip charge areas | Zip code databases, tech locations |

### Execution Plan

```
Wave 1 (parallel):  Manufacturer Census + Corporate Ownership + OEM & Supply Chain
                     |
                     v (feeds into)
Wave 2 (parallel):  Failure Patterns + Parts Intelligence
                     |
                     v (feeds into)
Wave 3 (sequential): Triage Flow Builder (synthesizes Wave 1 + 2)
Wave 4 (parallel):   Geography & Dispatch (independent)
```

### Equipment Categories

- Treadmills (highest priority)
- Stair steppers / StairMasters
- Ellipticals
- Exercise bikes (upright + recumbent)
- Rowing machines
- Cable machines / functional trainers
- Smith machines / home gyms
- Spin bikes (Peloton, etc.)

### Output

Each agent writes structured JSON to `~/.claude/ahgen/fitness-repair/research/`. A consolidation step merges everything into the SQLite reference database, deduplicates, and cross-references.

---

## 2. Deep Reference Database (SQLite)

Location: `~/.claude/ahgen/fitness-repair/fitness-repair.db`

### Schema

```sql
-- Core entities
CREATE TABLE manufacturers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  hq_country TEXT,
  website TEXT,
  status TEXT NOT NULL DEFAULT 'active',  -- active|defunct|acquired
  parent_company_id INTEGER REFERENCES manufacturers(id),
  notes TEXT
);

CREATE TABLE brands (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  manufacturer_id INTEGER NOT NULL REFERENCES manufacturers(id),
  name TEXT NOT NULL UNIQUE,
  equipment_types TEXT,     -- JSON array: ["treadmill","elliptical"]
  price_tier TEXT,          -- budget|mid|premium|commercial
  sold_at TEXT,             -- JSON array: ["Costco","Amazon","direct"]
  status TEXT NOT NULL DEFAULT 'active'  -- active|discontinued|rebranded
);

CREATE TABLE models (
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

-- Supply chain
CREATE TABLE oem_factories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  location TEXT,
  country TEXT,
  components_produced TEXT,  -- JSON: ["motors","controllers","frames"]
  brands_supplied TEXT       -- JSON array of brand names
);

CREATE TABLE parts_catalog (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  component_type TEXT NOT NULL,  -- motor|belt|controller|display|roller|bearing|etc
  oem_factory_id INTEGER REFERENCES oem_factories(id),
  compatible_model_ids TEXT,     -- JSON array
  cross_compatible_part_ids TEXT,-- JSON array
  typical_price_range TEXT,
  sources TEXT                   -- JSON array of {supplier, url, phone}
);

-- Failure intelligence
CREATE TABLE failure_patterns (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  equipment_type TEXT NOT NULL,
  component_type TEXT NOT NULL,
  symptom TEXT NOT NULL,
  root_cause TEXT,
  frequency TEXT,              -- common|occasional|rare
  typical_age_years INTEGER,
  diy_fixable INTEGER DEFAULT 0,
  requires_tech INTEGER DEFAULT 1,
  estimated_repair_cost TEXT,
  triage_priority INTEGER      -- 1-5, where 1 = check first
);

-- Triage decision trees
CREATE TABLE triage_flows (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  equipment_type TEXT NOT NULL,
  entry_symptom TEXT NOT NULL,
  decision_tree TEXT NOT NULL   -- JSON: nested {question, yes_branch, no_branch, resolution}
);

-- Service area
CREATE TABLE service_zones (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  zone_name TEXT NOT NULL,
  zip_codes TEXT NOT NULL,     -- JSON array
  rate_type TEXT NOT NULL,     -- standard|trip_charge
  trip_charge_amount REAL,
  tech_ids TEXT                -- JSON array
);

CREATE TABLE techs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  phone TEXT,
  email TEXT,
  base_state TEXT,             -- AZ or CA
  az_availability TEXT,        -- JSON: ["Mon","Tue","Wed","Thu","Fri"]
  ca_availability TEXT,        -- JSON: ["Sat","Sun"]
  zones TEXT,                  -- JSON array of zone_ids
  specialties TEXT,            -- JSON: ["treadmill","cable_machine"]
  active INTEGER DEFAULT 1
);

-- Call history
CREATE TABLE service_calls (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp TEXT NOT NULL DEFAULT (datetime('now')),
  caller_phone TEXT,
  equipment_type TEXT,
  brand TEXT,
  model TEXT,
  symptom TEXT,
  triage_result TEXT,
  tech_id INTEGER REFERENCES techs(id),
  scheduled_date TEXT,
  zone_id INTEGER REFERENCES service_zones(id),
  status TEXT DEFAULT 'scheduled'  -- scheduled|completed|cancelled|no_show
);
```

### Design Rationale

- **SQLite** — runs on Mac Mini alongside crm.db, zero infrastructure cost, matches existing patterns
- **Cross-referencing** — manufacturer ownership chains + OEM factories enable "one part fits 3 brands" intelligence
- **`service_calls` table** — builds real-world analytics over time to validate/correct swarm research

---

## 3. Distilled Voice Knowledge Base

Location: `~/.claude/ahgen/fitness-repair/knowledge-base.json`
Size target: 80-120KB
Auto-generated from SQLite database via `distill.py`

### Structure

```json
{
  "metadata": {
    "version": "1.0.0",
    "generated_from": "fitness-repair.db",
    "generated_at": "<timestamp>",
    "equipment_categories": 8,
    "brands_included": 30,
    "triage_flows": 24
  },
  "agent_persona": {
    "name": "Fitness Repair Service",
    "greeting": "Thanks for calling Fitness Repair. I can help with treadmills, ellipticals, stair steppers, and other heavy fitness equipment. What's going on with your machine?",
    "tone": "Friendly, knowledgeable repair tech. Short answers. One question at a time.",
    "closing": "Offer to schedule a tech visit or summarize next steps."
  },
  "service_area": {
    "core_zones": ["SoCal", "Phoenix Metro", "Tucson Metro"],
    "extended_zones": ["Inland Empire Extended", "AZ Rural"],
    "qualification_flow": "Ask city or zip. Core = standard rate. Extended = trip charge. Outside = politely decline with referral suggestion."
  },
  "brand_ownership_map": {},
  "equipment_types": {},
  "triage_flows": {},
  "universal_failure_patterns": {},
  "safety_rules": [
    "Burning smell or sparking: UNPLUG IMMEDIATELY, schedule tech, do not troubleshoot further",
    "Exposed wiring: UNPLUG, tech visit only",
    "Machine making grinding metal sounds: STOP USING, could cause injury",
    "Treadmill belt catching/grabbing: STOP USING, fall hazard"
  ],
  "scheduling_info": {
    "phone_hours": "Monday-Friday, 8am-5pm Pacific",
    "lead_time": "Usually within 2-3 business days",
    "availability_by_region": {
      "arizona": "Monday through Friday (weekdays)",
      "southern_california": "Saturday and Sunday (weekends)"
    },
    "talk_track_az": "Our tech is in the Arizona area during the week. What day works best — any weekday preference?",
    "talk_track_ca": "Our tech covers Southern California on weekends. Would Saturday or Sunday work better for you?",
    "talk_track_flexible": "Let me note that preference and we'll see what we can work out.",
    "what_to_collect": ["name", "phone", "address/zip", "equipment type", "brand and model if known", "brief issue description", "preferred day/time"],
    "do_not_promise": "Never confirm a specific appointment. Say: 'I'll pass this along and someone will confirm your appointment shortly.'"
  },
  "common_caller_scenarios": []
}
```

### Distillation Rules

- **Brands:** Top 30 by US market presence (covers ~95% of expected calls)
- **Triage flows:** Top 3 failure patterns per equipment type (~24 flows, covers ~80% of issues)
- **Talk tracks:** Conversational phrasing for voice, not technical manuals
- **Size target:** 80-120KB (proven sweet spot from sauna agent)
- **Regeneration:** On demand when the DB is updated

### What stays in the DB only

- Obscure/defunct brands (<1% call likelihood)
- Detailed parts cross-reference tables
- OEM factory details
- Full model-by-model specs
- Historical pricing data
- Service call analytics

### Unknown brand fallback

Talk track: "I don't have the specifics on that model handy. Let me get your info and have someone follow up with the details." Post-call processor flags the brand for DB enrichment.

---

## 4. Voice Agent & Call Flow

### Retell Bridge Integration

New agent registered in the existing multi-agent bridge at `~/.claude/ahgen/retell-bridge/`.

**New files:**
- `src/agents/fitness-repair.ts` — agent config + system prompt + KB injection
- `src/post-call/fitness-repair.ts` — transcript extraction (brand, model, issue, scheduling preferences)

**Modified files:**
- `src/agents/index.ts` — register fitness-repair agent
- `src/post-call/index.ts` — register fitness-repair handler (requires generalizing return type from `SaunaPostCallResult` to a union or generic)

**Agent config:**
- Model: `claude-sonnet-4-6` (fast for voice, smart for triage)
- Max tokens: 400 (short voice responses)
- Knowledge base: distilled JSON loaded at startup
- Separate Retell agent ID + phone number

### Call Flow

```
Phase 1: Identify Equipment
  - Equipment type (treadmill, elliptical, etc.)
  - Brand and model (if known)
  - Age of equipment
  - Symptom description

Phase 2: Triage
  - Safety check (unplug if burning/sparking/grinding)
  - Match symptom to triage flow from knowledge base
  - Walk through diagnostic steps one at a time
  - Determine: DIY fix or tech visit needed

Phase 3: Qualify & Collect (if tech visit needed)
  - Collect name and phone
  - Collect address/zip code
  - Check service area:
    - Core zone: standard rate
    - Extended zone: mention trip charge
    - Outside: politely decline with referral suggestion
  - Ask for preferred days/times
  - CRITICAL scheduling awareness:
    - Arizona customers: weekday availability only (Mon-Fri)
    - Southern California customers: weekend availability only (Sat-Sun)
    - Agent must frame this naturally: "Our tech is in your area on [weekdays/weekends],
      what works best for you?"
  - Do NOT promise a specific appointment — say "I'll pass this along and
    someone will confirm your appointment shortly"

Phase 4: Close
  - Recap: equipment, issue, what was determined
  - Confirm customer info collected
  - Set expectation: "You'll hear back to confirm scheduling"
  - "Anything else I can help with?"
```

### Scheduling Model

**Manual scheduling — no calendar automation.** One tech, manages his own calendar.

The voice agent's job is to collect everything the tech needs to decide and schedule:
- Customer contact info and location
- Equipment details and triage result
- Customer's preferred days/times
- Zone classification (standard vs trip charge)

The post-call processor writes a structured **service request** to the `service_calls` table and outputs a summary. The tech (or someone on his behalf) reviews pending requests and confirms appointments.

**Geographic availability constraint (baked into voice KB):**
- Tech is based in Arizona — available for AZ service calls Monday through Friday
- Tech travels to Southern California on weekends — available for SoCal calls Saturday and Sunday
- The voice agent MUST guide scheduling around this: "Our tech covers your area on [weekdays/weekends]"
- If a customer insists on a day outside the pattern, the agent says "Let me note that preference and we'll see what we can work out"

### Post-Call Processor Output

```typescript
interface FitnessRepairPostCallResult {
  equipment_type: string;
  brand?: string;
  model?: string;
  symptom: string;
  triage_result: 'diy_fix' | 'needs_tech' | 'safety_issue' | 'unknown';
  customer: {
    name?: string;
    phone: string;
    address?: string;
    zip?: string;
  };
  scheduling: {
    requested_days: string;        // "weekday" | "weekend" | specific days
    requested_time_window?: string; // "morning" | "afternoon" | specific
    zone: string;
    trip_charge: boolean;
    state: 'AZ' | 'CA';           // determines weekday vs weekend availability
  };
  flags: {
    unknown_brand: boolean;
    safety_issue: boolean;
    outside_service_area: boolean;
  };
}
```

---

## 5. Project Structure

### File Layout

```
~/.claude/ahgen/
  fitness-repair/
    fitness-repair.db            # Deep reference database
    knowledge-base.json          # Distilled voice KB
    distill.py                   # DB to JSON distillation script
    schema.sql                   # DB schema definition
    ingest.py                    # Research JSON to SQLite ingestion
    research/                    # Swarm output staging
      manufacturers.json
      ownership.json
      oem-supply-chain.json
      failure-patterns.json
      parts-intelligence.json
      triage-flows.json
      service-zones.json
    zones/
      zip-codes.json             # SoCal + AZ zip code to zone mapping

  retell-bridge/
    src/agents/
      index.ts                   # Modified: register fitness-repair
      fitness-repair.ts          # NEW
      sales.ts                   # existing
      sauna-service.ts           # existing
    src/post-call/
      index.ts                   # Modified: register handler, generalize return type
      fitness-repair.ts          # NEW
    .env                         # Add: RETELL_FITNESS_AGENT_ID, FITNESS_KB_PATH

~/.claude/skills/
  fitness-repair/
    SKILL.md                     # Claude Code management skill
```

### Implementation Phases

**Phase 1: Research Swarm**
- Dispatch 7 agents (Wave 1, 2, 3, 4)
- Output: 7 structured JSON files in research/
- Scope: one session, heavy web search

**Phase 2: Database & Distillation**
- Create schema, populate SQLite from research JSON
- Build distill.py for DB to voice KB generation
- Validate: query DB, spot-check distilled KB

**Phase 3: Voice Agent + Post-Call Processing**
- fitness-repair.ts agent config + system prompt with AZ/CA scheduling awareness
- fitness-repair.ts post-call processor (extract equipment, issue, customer, scheduling prefs)
- Generalize post-call/index.ts return type to support both sauna and fitness results
- Populate techs + service_zones tables
- Register in bridge, test with simulation script
- End-to-end test: call -> triage -> service request in DB

**Phase 4: Management Skill + Polish**
- /fitness-repair Claude Code skill
- Transcript review, call volume monitoring
- DB enrichment workflow for flagged unknown brands
- KB regeneration on demand

---

## 6. Out of Scope

- Automated calendar integration (manual scheduling for now; revisit when volume warrants)
- Customer-facing web portal
- SMS/email appointment confirmations
- Payment processing
- Inventory/parts management
- Retell dashboard setup (manual step)

---

## 7. Prerequisites

| Prerequisite | Status |
|-------------|--------|
| Retell bridge running | Already built |
| Retell account + API key | Already have |
| New Retell agent + phone number | Manual: Retell dashboard |
| Tech name, phone, email | Need from user |
| Tech zone assignments (which AZ + CA zips) | Need from user |
| Zip code to zone mapping | Built in Phase 1 (Geography agent) |
