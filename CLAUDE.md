# Soigneur

A personal cycling coach dashboard and chat assistant built with FastAPI, PydanticAI (Anthropic Claude), Jinja2 + HTMX, and DuckDB.

Analyzes completed workouts, upcoming training, sleep/HRV/readiness metrics, weather, and user mood/stress to provide context-aware coaching recommendations. Two modes: a deterministic dashboard (no LLM) and an agent-driven chat interface.

Key constraints: no JavaScript frameworks (HTMX only), all I/O async, secrets via Doppler, structured workouts are always indoors, outdoor rides are always unstructured.

<!-- AUTO-GENERATED BELOW - DO NOT EDIT -->

## Project Rules

Read the referenced files before starting work.

- **`.cursor/rules/architecture.mdc`** — Soigneur system architecture, data flows, and component relationships
- **`.cursor/rules/frontend.mdc`** — Frontend conventions for Soigneur — Jinja2, HTMX, and CSS
- **`.cursor/rules/project.mdc`** — Soigneur project overview and stack decisions
- **`.cursor/rules/python.mdc`** — Python coding conventions for Soigneur
- **`.cursor/rules/services.mdc`** — Services and agent layer conventions for Soigneur
- **`.cursor/rules/testing.mdc`** — Testing conventions for Soigneur — pytest and pytest-asyncio
