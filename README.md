# 💨 UK Wind Generation Forecast Intelligence Dashboard

> A full-stack monitoring application that compares **day-ahead wind generation forecasts** (Elexon `WINDFOR`) against **actual half-hourly metered outturn** (Elexon `FUELHH`) for Great Britain's electricity grid, with rigorous accuracy measurement enforcing a strict **10:00 UTC day-ahead decision cutoff**.

---

## Table of Contents

1. [Overview](#overview)
2. [Live Demo & Screenshots](#live-demo--screenshots)
3. [Architecture](#architecture)
4. [Project Structure](#project-structure)
5. [Setup — Local Development](#setup--local-development)
6. [Setup — Docker (Recommended)](#setup--docker-recommended)
7. [API Reference](#api-reference)
8. [Key Assumptions & Design Decisions](#key-assumptions--design-decisions)
9. [Accuracy Methodology](#accuracy-methodology)
10. [Testing](#testing)
11. [AI Assistance Disclosure](#ai-assistance-disclosure)
12. [Dependencies & Licences](#dependencies--licences)

---

## Overview

The UK electricity system relies on wind generation forecasts for trading and dispatch decisions made the **day before** delivery. This dashboard answers:

- **How accurate** are day-ahead wind forecasts for each half-hourly settlement interval?
- **Which direction** do forecast errors skew — over-forecasting or under-forecasting?
- **What is the magnitude** of error (MAE, RMSE, Bias) for a selected date range?

### Data Sources

| Dataset | API | Description |
|---|---|---|
| `FUELHH` | `GET /datasets/FUELHH` | Half-hourly metered generation outturn by fuel type (actual wind delivered to grid) |
| `WINDFOR` | `GET /datasets/WINDFOR` | Day-ahead wind generation forecasts (unconstrained NWP-based) |

Both datasets are sourced from the **[Elexon Balancing Mechanism Reporting Service (BMRS)](https://bmrs.elexon.co.uk/)** — the authoritative real-time source for GB electricity market data. No API key is required.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  Browser  →  http://localhost:3000                                   │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  Frontend  (React 18 + Vite, served by Nginx)                  │  │
│  │                                                                │  │
│  │   App.jsx          ← date pickers, presets, Run Analysis       │  │
│  │   MetricCard       ← MAE · RMSE · Bias · Count                 │  │
│  │   GenerationChart  ← SVG dual-line: Actual vs Forecast         │  │
│  │   ErrorChart       ← SVG signed error bars, zero baseline      │  │
│  │   InsightsPanel    ← Domain analysis of bias characteristics   │  │
│  │   IntervalsTable   ← Search · Pagination · CSV export          │  │
│  └──────────────────────────┬─────────────────────────────────────┘  │
│                             │ /api/*  (Nginx reverse proxy)          │
└─────────────────────────────┼───────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Backend  (FastAPI + Uvicorn, Python 3.12)   :8000                  │
│                                                                      │
│   GET /api/actuals     → elexon_client → FUELHH                     │
│   GET /api/forecasts   → elexon_client → WINDFOR                    │
│   GET /api/accuracy    → accuracy_service (10:00 UTC D-1 cutoff)    │
│   GET /api/health      → operational status                         │
│   GET /docs            → Swagger UI                                 │
│                                                                      │
│   Elexon API  ──────────────────────────────────────────────────►  │
│   (6-day chunking, synthetic fallback when offline)                 │
└─────────────────────────────────────────────────────────────────────┘
```

### Technology Choices

| Layer | Technology | Reason |
|---|---|---|
| Backend framework | FastAPI | Async-native, automatic OpenAPI docs, Python typing |
| HTTP client | httpx | Async, modern, mirrors requests API |
| Data validation | Pydantic V2 | Strict typing, clear error messages |
| Frontend | React 18 + Vite | Fast HMR, small bundle, no heavy UI framework needed |
| Charts | Hand-written SVG | Zero dependencies, full control, interactive hover |
| Production serving | Nginx | Serves static files + `/api` reverse proxy in one container |
| Containerisation | Docker + Compose | Reproducible builds, single-command deployment |

---

## Project Structure

```
wind-forecast-dashboard/
│
├── docker-compose.yml          ← Start everything with one command
├── .env.example                ← Environment variable template
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── pytest.ini
│   └── app/
│       ├── main.py             ← FastAPI app, CORS, router registration
│       ├── api/
│       │   ├── actuals.py      ← GET /api/actuals
│       │   ├── forecasts.py    ← GET /api/forecasts
│       │   └── accuracy.py     ← GET /api/accuracy
│       ├── services/
│       │   ├── elexon_client.py    ← FUELHH + WINDFOR fetcher, 6-day chunking
│       │   ├── accuracy_service.py ← MAE / RMSE / Bias, 10:00 UTC D-1 cutoff
│       │   └── forecast_service.py ← Cutoff-based forecast selector
│       └── schemas/
│           └── generation.py   ← Pydantic V2 request/response models
│   └── tests/
│       └── test_forecast_and_accuracy.py  ← 7 unit tests
│
└── frontend/
    ├── Dockerfile              ← Multi-stage: Node build → Nginx serve
    ├── nginx.conf              ← Reverse proxy + SPA fallback
    ├── vite.config.js
    └── src/
        ├── App.jsx
        └── components/
            ├── MetricCard.jsx
            ├── GenerationChart.jsx
            ├── ErrorChart.jsx
            ├── InsightsPanel.jsx
            └── IntervalsTable.jsx
```

---

## Setup — Local Development

### Prerequisites

- Python **3.12+**
- Node.js **18+** and npm
- (Optional) Git

### 1 — Clone the repository

```bash
git clone <your-repo-url>
cd wind-forecast-dashboard
```

### 2 — Backend

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

# Install dependencies
pip install -r requirements.txt

# Start the API server (hot-reload enabled)
uvicorn app.main:app --reload
```

Backend is available at **http://127.0.0.1:8000**
Interactive docs at **http://127.0.0.1:8000/docs**

### 3 — Frontend

Open a new terminal:

```bash
cd frontend

# Install dependencies
npm install

# Start Vite dev server (proxies /api → backend automatically)
npm run dev
```

Dashboard is available at **http://localhost:5173**

---

## Setup — Docker (Recommended)

The fastest way to run the full stack. Requires **Docker Desktop**.

```bash
# Build images and start both services
docker compose up --build

# Or run in the background
docker compose up -d --build
```

| URL | Description |
|---|---|
| `http://localhost:3000` | React dashboard |
| `http://localhost:8000/docs` | Swagger UI |
| `http://localhost:8000/api/health` | Health check |

```bash
# View live logs
docker compose logs -f

# Stop everything
docker compose down
```

> **Note:** The first build downloads base images (Python 3.12-slim + Node 20 + Nginx). Subsequent builds are fast because Docker caches each layer.

---

## API Reference

### `GET /api/actuals`

Returns half-hourly wind generation outturn from Elexon `FUELHH`.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `from_date` | date | 2 days ago | Start date `YYYY-MM-DD` |
| `to_date` | date | today | End date `YYYY-MM-DD` |
| `fuel_type` | string | `WIND` | Fuel category |

### `GET /api/forecasts`

Returns wind generation forecasts from Elexon `WINDFOR`.

| Parameter | Type | Description |
|---|---|---|
| `from_date` | date | Target delivery start |
| `to_date` | date | Target delivery end |
| `publish_from` | datetime | Filter by publish time (optional) |
| `publish_to` | datetime | Filter by publish time (optional) |
| `cutoff_hours` | float | Select latest forecast X hours before interval (optional) |

### `GET /api/accuracy`

Computes MAE, RMSE, and Bias for a date range.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `start_date` | date | `2026-01-01` | First delivery date |
| `end_date` | date | `2026-01-31` | Last delivery date |

**Example response:**

```json
{
  "dataset": "FUELHH + WINDFOR",
  "start_date": "2026-01-01",
  "end_date": "2026-01-02",
  "decision_cutoff": "10:00 UTC on the day before delivery",
  "count": 48,
  "mae": 3715.29,
  "rmse": 3806.53,
  "bias": 3715.29,
  "intervals": [
    {
      "startTime": "2026-01-01T00:00:00+00:00",
      "forecastPublishTime": "2025-12-31T08:30:00+00:00",
      "forecast": 12400.0,
      "actual": 8900.0,
      "error": 3500.0,
      "absoluteError": 3500.0
    }
  ]
}
```

### `GET /api/health`

Returns `{ "status": "healthy" }`. Used by Docker health checks.

---

## Key Assumptions & Design Decisions

### 1. Decision Cutoff: 10:00 UTC Day-Ahead

The challenge states that trading decisions are made **before 10:00 UTC on the day before delivery**. The accuracy engine enforces this strictly:

```
Cutoff(interval) = interval.startTime.replace(hour=10, minute=0) − 1 day
```

Only forecasts with `publishTime ≤ cutoff` are eligible. Among eligible forecasts, the **latest** (most recently published before the cutoff) is selected. Forecasts published at `10:00:01` or later are rejected.

### 2. WINDFOR vs FUELHH — Structural Difference

`WINDFOR` models **unconstrained atmospheric wind generation potential** (NWP-based).
`FUELHH` records **net metered outturn delivered to the grid**.

These are not the same quantity. Actual delivery may be lower than forecast due to:
- Transmission curtailment (e.g. B6 Anglo-Scottish export boundary thermal limits)
- High-wind turbine cut-out protection at storm speeds (~25 m/s)
- Planned and unplanned availability constraints

This structural difference is the principal reason errors are consistently positive (Forecast > Actual). It is a known characteristic of the UK electricity market, not a data or calculation error. The InsightsPanel presents these as **potential contributing factors**, not confirmed causes.

### 3. Timestamp Normalisation

Elexon `WINDFOR` records frequently include sub-second precision (e.g. `12:00:00.246Z`). Without normalisation, `12:00:00.000Z` and `12:00:00.246Z` would not match the same settlement interval. All timestamps are normalised to second precision and converted to UTC before matching:

```python
result.astimezone(timezone.utc).replace(second=0, microsecond=0)
```

### 4. 6-Day Chunking for Elexon API

Elexon's BMRS API rejects requests spanning more than **7 calendar days** with `HTTP 400`. The client automatically splits large date ranges into ≤ 6-day chunks, fetches each sequentially, and returns a unified list. This is transparent to callers.

### 5. Synthetic Offline Fallback

If the Elexon API is unreachable (network error, timeout, or empty response), the backend generates **deterministic synthetic data** based on a realistic GB wind profile (3,000–16,000 MW range). This ensures the frontend always renders a meaningful result, even in offline/test environments. Synthetic data is clearly distinguishable from live data by its perfectly regular sinusoidal pattern.

### 6. Frontend Charts — Pure SVG

All charts (line chart, error bar chart) are rendered with hand-written SVG elements inside React components. No charting library (Chart.js, Recharts, D3) was used. This keeps the bundle small and gives full control over layout, colouring, and hover behaviour.

---

## Accuracy Methodology

Given a set of matched `(actual, forecast)` pairs across $N$ settlement intervals:

$$\text{MAE} = \frac{1}{N} \sum_{i=1}^{N} |F_i - A_i|$$

$$\text{RMSE} = \sqrt{\frac{1}{N} \sum_{i=1}^{N} (F_i - A_i)^2}$$

$$\text{Bias} = \frac{1}{N} \sum_{i=1}^{N} (F_i - A_i)$$

Where:
- $F_i$ = selected forecast for interval $i$ (latest eligible before 10:00 UTC D-1)
- $A_i$ = actual metered outturn for interval $i$
- Positive Bias → systematic over-forecasting
- Negative Bias → systematic under-forecasting

All values are in **megawatts (MW)**.

---

## Testing

```bash
cd backend
venv\Scripts\activate          # Windows
pytest tests/ -v
```

### Test Results

```
tests/test_forecast_and_accuracy.py::test_calculate_accuracy_basic               PASSED
tests/test_forecast_and_accuracy.py::test_calculate_accuracy_cutoff_strictly_enforced  PASSED
tests/test_forecast_and_accuracy.py::test_calculate_accuracy_empty_records        PASSED
tests/test_forecast_and_accuracy.py::test_calculate_accuracy_corrupt_data         PASSED
tests/test_forecast_and_accuracy.py::test_parse_datetime_subsecond_normalization  PASSED
tests/test_forecast_and_accuracy.py::test_mock_fallback_profile_generation        PASSED
tests/test_forecast_and_accuracy.py::test_api_date_validation                     PASSED

7 passed in 1.28s
```

### What is Tested

| Test | Validates |
|---|---|
| `test_calculate_accuracy_basic` | Correct MAE, RMSE, Bias with known inputs; correct forecast selection |
| `test_calculate_accuracy_cutoff_strictly_enforced` | Forecast at exactly 10:00 UTC is eligible; 10:01 UTC is rejected |
| `test_calculate_accuracy_empty_records` | Empty inputs → count=0, metrics=null, clear message |
| `test_calculate_accuracy_corrupt_data` | Non-numeric generation and null timestamps are silently skipped |
| `test_parse_datetime_subsecond_normalization` | `12:00:00.246Z` == `12:00:00Z` after normalisation |
| `test_mock_fallback_profile_generation` | Synthetic data produces 48 intervals/day in realistic MW range |
| `test_api_date_validation` | Inverted date range (`end < start`) returns HTTP 400 |

---

## AI Assistance Disclosure

This project was developed with the assistance of **Google Antigravity (powered by Claude Sonnet / Gemini)**, an AI pair-programming tool. The following section documents exactly how AI was used, what was independently reasoned, and what was verified manually.

---

### What AI helped with

| Area | AI Contribution |
|---|---|
| **Boilerplate scaffolding** | Initial FastAPI router structure, Pydantic schema definitions, Vite config |
| **Elexon API debugging** | Diagnosing `400 Bad Request` errors caused by >7-day query windows; suggesting the 6-day chunking fix |
| **Timestamp normalisation** | Identifying that `WINDFOR` timestamps include milliseconds (`.246Z`) and suggesting `.replace(second=0, microsecond=0)` |
| **SVG chart layout** | X-axis tick spacing algorithm, SVG `viewBox` and `polyline` syntax |
| **Nginx configuration** | `try_files $uri /index.html` SPA fallback, proxy timeout values |
| **Dockerfile** | Multi-stage frontend build (Node → Nginx), health check command |
| **Test structure** | pytest fixture patterns and synchronous coroutine testing on Windows |
| **README formatting** | Markdown structure, table layouts, section ordering |

---

### What was independently reasoned and verified

| Area | Human Decision |
|---|---|
| **10:00 UTC D-1 decision cutoff** | Read from the challenge specification; cutoff logic reviewed and confirmed correct |
| **WINDFOR vs FUELHH structural difference** | Domain knowledge — WINDFOR is unconstrained NWP; FUELHH is metered outturn post-curtailment |
| **Positive bias explanation** | Researched GB electricity market: B6 curtailment, BOA instructions, cut-out thresholds |
| **Forecast selection rule** | Latest-eligible (not earliest) is the correct approach for day-ahead trading |
| **Synthetic fallback strategy** | Decision to use realistic sinusoidal GB wind profile rather than random or zero values |
| **InsightsPanel language softening** | Deliberate editorial choice to present bias causes as "potential factors" not confirmed conclusions |
| **API response schema** | Reviewed and approved all response field names and types |

---

### AI tool limitations acknowledged

- AI suggestions were **reviewed before being applied**. No code was blindly accepted.
- All **accuracy calculations** (MAE, RMSE, Bias formulae) were independently verified against textbook definitions.
- The **10:00 UTC cutoff logic** was traced through `accuracy_service.py` line-by-line to confirm it matches the challenge specification.
- AI cannot access the live Elexon API. All API integration was **tested manually** using real Elexon responses verified through the `/docs` Swagger UI.
- **Domain explanations** (curtailment, B6 boundary, cut-out speeds) reflect genuine GB electricity market knowledge, not AI-generated speculation.

---

### Summary statement

> AI tools were used to accelerate development of standard patterns (boilerplate, Dockerfile, test structure) and to diagnose specific technical bugs (API query limits, timestamp precision). All business logic, accuracy methodology, domain interpretation, and final code review were performed by the developer. The AI assistant functioned as a knowledgeable pair-programming partner, not as an autonomous author.

---

## Dependencies & Licences

### Backend (Python)

| Package | Version | Licence |
|---|---|---|
| FastAPI | latest | MIT |
| Uvicorn | latest | BSD |
| httpx | latest | BSD |
| Pydantic | v2 latest | MIT |
| pandas | latest | BSD |
| python-dotenv | latest | BSD |
| pytest | latest | MIT |

### Frontend (Node)

| Package | Version | Licence |
|---|---|---|
| React | 18.x | MIT |
| react-dom | 18.x | MIT |
| Vite | 6.x | MIT |
| @vitejs/plugin-react | 4.x | MIT |

### Infrastructure

| Tool | Licence |
|---|---|
| Nginx 1.27 Alpine | BSD-like |
| Docker / Docker Compose | Apache 2.0 |
| Python 3.12 slim | PSF |
| Node 20 slim | MIT |

---

## Data Attribution

All electricity market data is sourced from the **Elexon Balancing Mechanism Reporting Service (BMRS)**:

> © Elexon Limited. Data available at [https://bmrs.elexon.co.uk](https://bmrs.elexon.co.uk) under Elexon's standard data licence terms. No API key is required for the public BMRS API endpoints used in this project.

---

*Built for the REint Full Stack SWE Challenge.*
