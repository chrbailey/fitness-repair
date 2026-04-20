# Fitness Repair Voice Agent

AI-powered voice agent for fitness equipment repair services covering Southern California and Arizona.

**Status:** v0.1 experimental. Research swarm and reference database are complete and test-covered. The Retell voice integration is author-only — it runs against a private Retell workspace with a purchased phone number and is not exercised in CI. See "What this is NOT" below before forking.

## What This Is

A research + knowledge-base project that:
1. **Researched** every major fitness equipment manufacturer, corporate ownership chain, Chinese OEM supply chain, common failure pattern, and parts-intelligence source using a multi-agent swarm (output committed under `research/`).
2. **Built** a deep SQLite reference database (`db/schema.sql`, 10 tables) and a distilled voice knowledge base (`knowledge-base/knowledge-base.json`, ~155 KB).
3. **Covers** treadmills, stair steppers, ellipticals, exercise bikes, rowing machines, cable machines, smith machines, and spin bikes.
4. **Connects** to Retell.ai for inbound phone call handling — triages equipment issues, walks callers through diagnostics, and collects service request details.

The research artefacts (`research/*.json`) and the distilled KB (`knowledge-base/knowledge-base.json`) are published in this repo. They are useful on their own as a dataset even if you never wire up the voice side.

## What This Is NOT

- **Not a general fitness-equipment service SaaS.** This is one operator's working setup. Service zones cover SoCal + AZ. Scheduling rules, brand coverage, and pricing hints are calibrated for that operator.
- **Not drop-in for another repair business.** You would keep the schema, ingestion pipeline, and distillation logic, but you would rewrite the research JSON (brand list, parts sources, OEM factories) and the zones config (zip codes, availability windows, trip charges).
- **Not CI-testable end-to-end.** Tests cover ingestion and distillation. Retell integration requires a live workspace, a phone number, and API credentials — it is out of scope for CI and stays manual.
- **Not proprietary data.** Research is synthesised from public sources (manufacturer sites, industry reporting, parts suppliers). Accuracy is "good enough for triage", not "good enough to repair without confirming".
- **Not a production voice agent right now.** Phase 1 (research + DB) is complete. The Retell agent definition is shaped but not yet receiving calls at scale.

## Architecture

```
Research Swarm (7 JSON outputs)
        │
        ▼
 db/ingest.py  ──►  SQLite reference DB
                    (10 tables, full intelligence)
                            │
                            ▼
                 db/distill.py  ──►  knowledge-base.json
                                     (~155 KB, voice-shaped)
                                            │
                                            ▼
                                  Retell.ai voice agent
                                  (inbound calls: triage → collect info → service request)
```

## Service Area

- **Arizona**: weekday service (Mon-Fri)
- **Southern California**: weekend service (Sat-Sun)
- Core zones at standard rate; extended zones with trip charge.
- Zip codes live in `zones/zip-codes.json`.

## Project Structure

```
docs/
├── specs/             Design specs (voice agent design, 2026-03-21)
└── plans/             Implementation plan (2026-03-21)
research/              Multi-agent swarm output
├── manufacturers.json        (~36 KB)  Major manufacturers, HQ, status, lines
├── ownership.json            (~27 KB)  Parent-subsidiary chains
├── oem-supply-chain.json     (~37 KB)  Chinese + US factories, shared components
├── failure-patterns.json     (~66 KB)  Symptoms, causes, DIY vs tech, ages
├── parts-intelligence.json   (~48 KB)  Brand-specific + universal suppliers
├── service-zones.json        (~23 KB)  Zone definitions, availability windows
└── triage-flows.json         (~91 KB)  Decision trees per equipment type + symptom
db/
├── schema.sql         (~3.7 KB)  10-table reference schema
├── ingest.py          (~6.4 KB)  Load research JSON into SQLite
├── distill.py         (~7.3 KB)  Shrink DB into voice-shaped KB JSON
├── test_ingest.py     (16 tests) Sample research → SQLite correctness
└── test_distill.py    (idem)     Populated DB → KB JSON correctness
knowledge-base/
└── knowledge-base.json (~155 KB) Distilled voice KB — what Retell sees
zones/
└── zip-codes.json     (~36 KB)  ZIP → zone mapping
```

## Setup (60 seconds to tests green)

```bash
git clone https://github.com/chrbailey/fitness-repair.git
cd fitness-repair
python3 -m venv .venv && source .venv/bin/activate
pip install pytest

cd db
python -m pytest test_ingest.py test_distill.py -v
```

Expected: 16 tests passed in under 1 second. Tests use `tmp_path` fixtures — no real data is written, no external services are called.

## Regenerating the Voice KB

```bash
cd db
python ingest.py   ../research   ../fitness.db
python distill.py  ../fitness.db ../knowledge-base/knowledge-base.json
```

The KB file committed to the repo was generated this way on 2026-03-22.

## How the Tests Cover the DB Layer

`db/test_ingest.py` (9 tests):

- All 10 tables created by schema.
- Manufacturers ingested correctly.
- Parent-subsidiary links resolve.
- Failure patterns, triage flows, service zones, OEM factories, parts catalog all land.
- Ingestion is idempotent — running twice does not duplicate rows.

`db/test_distill.py` (7 tests):

- Output is valid JSON.
- All required sections present (metadata, agent_persona, service_area,
  brand_ownership_map, equipment_types, triage_flows,
  universal_failure_patterns, safety_rules, scheduling_info).
- Scheduling splits AZ vs CA correctly.
- Triage flows make it into the KB.
- Size is within target.
- Persona carries the right greeting and tone.
- Safety rules include the "UNPLUG" directive.

## Known Limitations

- **No Retell integration tests in CI.** Retell is a live external service. Testing the voice agent requires a real phone number and costs real money. Those tests stay local.
- **Research is point-in-time.** The JSON was captured in March 2026. Ownership changes, OEM shifts, and new failure patterns will require re-running the research swarm.
- **Triage flows are generic by equipment type.** They are not brand-specific beyond what the failure-pattern data encodes. A NordicTrack-specific quirk that does not generalise to other treadmills may be missed.
- **Safety rules are not a substitute for a licensed technician.** The agent directs callers to unplug, to stop using equipment that sparks, and to schedule a visit when DIY is not safe — but it is a triage tool, not a repair instruction manual.
- **No tests for the Retell LLM bridge.** That layer is not in this repo.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Security issues: [SECURITY.md](SECURITY.md). Changes: [CHANGELOG.md](CHANGELOG.md).

## License

MIT (see [LICENSE](LICENSE)).
