# Contributing

Thanks for looking.

## Before opening a PR

1. **Open an issue first** for anything larger than a typo.
2. **Match the existing structure.** Research output, DB schema, and voice KB all have specific shapes — follow them.
3. **Run any tests that exist locally** before submitting.

## What this project will not accept

This repo powers a live Retell.ai voice agent that answers phone calls from fitness equipment owners. Changes that could degrade call quality or leak caller PII will not land.

- PRs that send caller PII (names, phone numbers, addresses, equipment serial numbers) to any third-party service other than Retell.ai itself.
- PRs that enlarge the distilled voice knowledge base beyond roughly 120KB — the voice agent prompt has a size ceiling and bloat directly hurts call latency.
- PRs that remove the service area logic (AZ weekdays, SoCal weekends, core vs extended zones). The zones are not a suggestion; they are dispatch reality.
- PRs that add external runtime dependencies to the voice agent prompt. The voice KB is a static JSON artifact — keep it that way.
- PRs that inject unvetted manufacturer or parts data into the reference DB without citing sources. The agent repeats this information to callers; wrong data becomes a support incident.

## Reporting security issues

See [SECURITY.md](SECURITY.md). Do not file security issues in the public tracker.

## Author

[Christopher Bailey](https://github.com/chrbailey).
