# Soigneur

A personal cycling coach dashboard and chat assistant.

Soigneur analyzes your completed workouts, upcoming scheduled training, sleep, and readiness data to help you make smarter daily training decisions. The name comes from cycling: a soigneur is the person who takes care of the rider's needs. This app does the same, but for training.

---

## What It Does

- **Dashboard** — calendar view of the past 30 days of completed workouts and upcoming scheduled workouts, today's readiness and sleep metrics (via Oura), and current weather
- **Daily check-in** — quick mood and stress inputs that inform the agent's recommendations
- **Chat interface** — ask your coach questions: should I do today's workout, how did this compare to similar efforts, what should I do instead?
- **Smart recommendations** — agent weighs HRV, sleep, mood, stress, training load, goals, and weather to give context-aware advice
- **Mental reset mode** — agent knows that an unstructured outdoor ride is sometimes the right call

---

## Data Sources

| Source | What It Provides |
|--------|-----------------|
| [intervals.icu](https://intervals.icu) | Completed workouts, HRV, sleep, readiness, workout notes |
| TrainerRoad (iCal feed) | Upcoming scheduled workouts |
| [Open-Meteo](https://open-meteo.com) | Weather (free, no API key required) |
| Oura (via intervals.icu) | Sleep score, total sleep time, readiness |

---

## Stack

- **Backend:** Python 3.14, FastAPI, PydanticAI (Anthropic Claude)
- **Frontend:** Jinja2 templates, HTMX — no JavaScript frameworks
- **Database:** DuckDB (chat history, check-ins, goals, auth)
- **Package manager:** uv
- **Secrets management:** Doppler
- **Linter/formatter:** Ruff
- **Deployment:** Railway

---

## Local Development

### Prerequisites
- Python 3.14+
- [uv](https://docs.astral.sh/uv/)
- [Doppler CLI](https://docs.doppler.com/docs/install-cli)

### Setup

```bash
git clone https://github.com/yourusername/soigneur.git
cd soigneur

# Install dependencies
uv sync

# Authenticate with Doppler (one-time)
doppler login
doppler setup
```

### Environment Variables

Secrets are managed via Doppler. The following variables must be configured in your Doppler project:

```
ANTHROPIC_API_KEY
INTERVALS_API_KEY
INTERVALS_ATHLETE_ID
TRAINERROAD_ICAL_URL
LOCATION_ZIP
```

### Run

```bash
doppler run -- uv run uvicorn app.main:app --reload
```

Open [http://localhost:8000](http://localhost:8000).

---

## Project Structure

```
app/
  main.py              # FastAPI entry point
  routers/             # Route handlers
  services/            # External data fetching (intervals.icu, TrainerRoad, weather)
  agents/              # PydanticAI agent, tools, and shared models
  templates/           # Jinja2 HTML templates
  static/              # CSS and static assets
tests/
  unit/
  integration/
  conftest.py
.cursor/rules/         # Cursor AI project rules
.env.example           # Documents required env vars — no values
pyproject.toml
```

---

## License

GNU General Public License v3.0 — see [LICENSE](LICENSE) for details.