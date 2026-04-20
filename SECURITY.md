# Security

## Responsible Disclosure

If you find a security issue, please do **not** file a public GitHub issue.

Email: chris.bailey@erp-access.com — include "SECURITY: fitness-repair" in the subject line.

Expect an acknowledgment within 72 hours.

## What this tool does

Fitness Repair runs a Retell.ai-backed voice agent for inbound fitness-equipment service calls across Southern California and Arizona. A multi-agent research swarm compiles manufacturer, OEM, failure-pattern, and parts data into a SQLite reference database. A distilled 80-120KB JSON voice knowledge base is extracted from that database and shipped to the Retell agent. The voice agent triages caller issues, walks through diagnostics, and collects service-request information.

Inbound calls contain caller PII: names, phone numbers, addresses, equipment identifiers, and spoken account of the issue.

## What this tool does NOT do

- It does not send caller PII to any third party other than Retell.ai (which handles the call infrastructure).
- It does not process payment information — payment collection happens outside this system.
- It does not auto-dispatch a technician or commit a schedule — it collects a service request for human review.
- It does not provide medical, legal, or safety-critical advice during calls beyond equipment-usage guidance from the voice KB.
- It does not retain call recordings or transcripts in this repository. Those live in Retell and downstream CRM systems.

## Known Considerations

- The voice KB (`knowledge-base/*.json`) is the agent's full prompt context. If incorrect manufacturer or parts data is committed, the agent will confidently repeat it to callers. Treat KB commits with more care than ordinary code commits.
- Service-area zones (`zones/`) directly affect dispatch. Incorrect zone mappings send techs to wrong addresses or decline valid calls.
- Retell API keys and phone-line credentials are not stored in this repo and must not be. Use environment variables and local `.env` files (mode 600).
- The research swarm output under `research/` may include scraped manufacturer documentation. If a specific manufacturer requests removal, honor it.

If you see evidence of any of the "does NOT do" items, that is a security issue — please report.
