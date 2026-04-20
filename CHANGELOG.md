# Changelog

All notable changes to fitness-repair are documented here.

The format is loosely based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- CI workflow (`.github/workflows/tests.yml`) — runs `db/test_ingest.py` and
  `db/test_distill.py` on Python 3.9, 3.10, 3.11, 3.12.
- This CHANGELOG.

### Changed
- README rewritten with "What this is NOT", scope labels, service-area
  calibration caveats, and a 60-second reproduction path.
- LICENSE noted as MIT in README (previously said "Proprietary" — mismatch
  with the committed MIT LICENSE file).

## [0.1.0] — 2026-03-22

### Added
- Research Swarm — Waves 1, 2, 3, 4 complete:
  - 68 documented failure patterns.
  - 50 brand-specific parts sources.
  - Manufacturer list with HQ, status, product lines.
  - Ownership / subsidiary chains.
  - Chinese + US OEM factory map.
  - Service zone definitions for SoCal + AZ.
  - Triage decision trees per equipment type + entry symptom.
- Database schema (`db/schema.sql`) — 10 tables: manufacturers, brands,
  oem_factories, models, parts_catalog, failure_patterns, triage_flows,
  service_zones, techs, service_calls.
- Ingestion pipeline (`db/ingest.py`) — loads research JSON into SQLite,
  idempotent, resolves parent-subsidiary links in a second pass.
- Distillation pipeline (`db/distill.py`) — shrinks reference DB into a
  ~155 KB voice knowledge base JSON for the Retell agent.
- 16 tests across `test_ingest.py` (9) and `test_distill.py` (7).
- Zip code → zone mapping under `zones/zip-codes.json`.
- Implementation plan (`docs/plans/2026-03-21-...md`) and voice-agent design
  spec (`docs/specs/2026-03-21-...md`).
- Python 3.9 compatibility (`from __future__ import annotations`,
  `Union[dict, list]` rather than `dict | list`).
