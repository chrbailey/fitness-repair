# Fitness Repair Voice Agent

AI-powered voice agent for fitness equipment repair services covering Southern California and Arizona.

## What This Is

A multi-agent system that:
1. **Researches** every major fitness equipment manufacturer, corporate ownership chains, Chinese OEM supply chains, common failure patterns, and parts intelligence
2. **Builds** a deep SQLite reference database and distilled voice knowledge base
3. **Answers phone calls** via Retell.ai — triages equipment issues, walks callers through diagnostics, and collects service request details
4. **Covers** treadmills, stair steppers, ellipticals, exercise bikes, rowing machines, cable machines, smith machines, and spin bikes

## Architecture

```
Research Swarm (7 agents)
    |
    v
SQLite Reference DB (full intelligence)
    |
    v
Distilled Voice KB (80-120KB JSON, top 30 brands, 24 triage flows)
    |
    v
Retell Voice Agent (phone calls: triage -> collect info -> service request)
```

## Service Area

- **Arizona**: Weekday service (Mon-Fri)
- **Southern California**: Weekend service (Sat-Sun)
- Core zones at standard rate, extended zones with trip charge

## Project Structure

```
docs/specs/          # Design specifications
research/            # Multi-agent swarm output (manufacturer, ownership, OEM, failures, parts data)
db/                  # SQLite schema and ingestion scripts
knowledge-base/      # Distilled voice KB (auto-generated from DB)
zones/               # Service area zip code mappings
```

## Status

Phase 1: Research Swarm — IN PROGRESS

## License

Proprietary
