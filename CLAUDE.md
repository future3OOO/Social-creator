# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Rental Listing Social Media Agent — a Python async pipeline that takes a TradeMe rental listing URL and automatically scrapes it, selects the best images, generates platform-optimized copy via Claude, and publishes to Facebook + Instagram.

**Status:** Core pipeline implemented (scraper, images, copy gen, publisher) with FastAPI backend and React frontend. `rental-agent-spec.md` contains the original specification.

## Pipeline Architecture

```
URL → [Scrape] → [Select Image] → [Generate Copy] → [Publish to FB + IG]
```

Four standalone async functions, no frameworks or orchestration layers. Each step is independently callable.

1. **Scrape** — Playwright headless browser hits TradeMe's JS-rendered SPA. Extracts via JSON-LD → `__NEXT_DATA__` → DOM fallback chain.
2. **Select Image** — Scores images by resolution × aspect ratio using Pillow. Resizes to 1080×1350 (IG 4:5) or 1080×1080 (FB square).
3. **Generate Copy** — Anthropic Claude (`claude-sonnet-4-5-20250514`) produces JSON with `facebook` and `instagram` keys. FB: 80-150 words, 0-1 hashtags, includes link. IG: 60-100 words, 5-7 hashtags, no links, "Link in bio".
4. **Publish** — Meta Graph API v22.0. FB uses `/{page_id}/photos` (single) or `/{page_id}/feed` with `attached_media[]` (multi). IG creates media containers, polls status, then publishes. Carousel support for 2-10 images.

## Setup & Commands

```bash
pip install playwright beautifulsoup4 httpx Pillow anthropic
playwright install chromium
```

Entry point: `python main.py` (interactive CLI — paste a TradeMe URL).

## Environment Variables

- `ANTHROPIC_API_KEY` — Claude API key
- `FB_PAGE_ID` — Facebook page ID
- `IG_USER_ID` — Instagram business account ID
- `META_PAGE_TOKEN` — Never-expiring page access token (setup steps in spec)

## Infrastructure & Deployment

This project shares the Hetzner VPS (`hetzner-chch`, user `codex`) with the Property Partner site (`/home/prop_/projects/property-partner-site`).

**Existing infrastructure to leverage:**
- **TradeMe scraper**: `property-partner-site/scraper/scraper.py` is a production-proven Playwright scraper for TradeMe's JS SPA (office page `5713372`). Uses photo ID extraction from `trademe.tmcdn.co.nz/photoserver` URLs and Pillow-based image optimization (quality=92 JPEG). Adapt for single-listing scraping.
- **Image hosting**: Scraped images live at `/var/www/propertypartner/listings/tm-{id}/` — publicly accessible over HTTPS via Nginx. This solves Instagram's requirement for publicly accessible image URLs.
- **Web server**: Nginx on `propertypartner.co.nz` with SSL via Certbot. Can serve listing images from existing `/listings/` directory or a new subdirectory.
- **Deployment pattern**: `rsync` to Hetzner, cron for scheduled tasks (existing scraper runs daily at 6 AM UTC), logs to `/home/codex/logs/`.
- **Python 3.12.3** with venv on the server.

## Quality Bar

Adapted from the Valua production quality policy. Follow these on every change.

### Production Loop

**Build | Understand | Clean | Polish | Prove | Repeat**

1. **Build** — Implement the agreed spec only. No scope creep.
2. **Understand** — Trace the flow end-to-end. Capture inputs, outputs, side-effects, invariants.
3. **Clean** — Remove dead code, collapse indirection, tighten APIs, reduce dependencies.
4. **Polish** *(after Clean)* — Optimize the hot path, reduce copies, simplify data structures, cache or precompute.
5. **Prove** — Tests pass, static checks clean, no regressions.
6. **Time Rule** — For every unit spent building, invest two units in Understand + Clean + Polish before the next slice.
7. **Exit Criteria** — Two clean passes completed; <2% gain remaining; code size stable or smaller.

**Never:** add features before polishing the current slice; expand APIs without real need; leave TODOs or bloat behind.

### Cleanup Rule

**All temporary files, artifacts, and remote resources created during a task MUST be cleaned up once the task completes.** No exceptions.

- Temporary images uploaded to the server for Meta API access must be deleted immediately after publishing completes (success or failure).
- Local temp files (processed images, intermediate outputs) must be cleaned up after the pipeline finishes.
- Never leave orphaned files on the server — the Hetzner VPS is shared infrastructure and must stay clean.
- Think about the full lifecycle of every resource you create: where does it live, how long does it need to exist, and what cleans it up?

### Root Cause Doctrine

- A slice is not "done" until the true root cause is fixed (no band-aids).
- Flow: reproduce → trace failing path → add guards/tests → repair correct layer → verify end-to-end.
- Never: catch-and-ignore, magic sleeps/retries, hiding faults behind flags.

### Python Code Quality Rules

- **No `# type: ignore`** as a shortcut. Fix the actual type issue.
- **No bare `except:`** or `except Exception: pass`. Handle specific exceptions; if best-effort cleanup is needed, log or explicitly suppress with a comment explaining why.
- **Validate at boundaries**: API responses, scraped DOM data, and external input are untrusted. Validate/parse into typed structures at the edge; keep the core strictly typed.
- **No `Any` annotations** unless truly unavoidable (e.g., third-party SDK gap). If unavoidable, confine behind a boundary with runtime validation.
- **Type hints on all function signatures** — args and return types.
- **Docstrings on exported/public functions** — emphasize "why", invariants, and edge-case behavior. Don't restate the function name. Trivial private helpers may omit.
- **Minimal code** — no wrapper functions for one-time operations, no premature abstractions, no "just in case" error handling. Three similar lines are better than a premature helper.

### Daily Micro-Cycle

1. **PLAN** — Outline APIs, data shapes, and tests.
2. **DRAFT** — Produce minimal code + test scaffolding.
3. **RUN & REVIEW** — Execute, then self-critique: spec alignment, edge cases, quality, simpler refactors.

## Key Conventions

- **Async-first**: all pipeline functions are `async def`, entry point uses `asyncio.run()`
- **Pure functional pipeline**: standalone functions that chain together, no middleware
- **snake_case** for functions/variables, **PascalCase** for classes (e.g., `MetaPublisher`), **UPPER_CASE** for constants
- The spec (`rental-agent-spec.md`) contains reference implementations for all four steps — use these as the starting templates
