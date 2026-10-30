# 💨 UK Wind Generation Forecast Intelligence Dashboard

> A production-ready full-stack monitoring application that compares **day-ahead wind generation forecasts** (Elexon `WINDFOR`) against **actual half-hourly metered outturn** (Elexon `FUELHH`) for Great Britain's electricity grid, with rigorous accuracy measurement enforcing a strict **10:00 UTC day-ahead decision cutoff**.

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Project Structure](#project-structure)
4. [Setup — Local Development](#setup--local-development)
5. [Setup — Docker (Recommended)](#setup--docker-recommended)
6. [API Reference](#api-reference)
7. [Key Assumptions & Design Decisions](#key-assumptions--design-decisions)
8. [Data Lineage: Live vs Synthetic Fallback](#data-lineage-live-vs-synthetic-fallback)
9. [Accuracy Methodology](#accuracy-methodology)
10. [Testing](#testing)
11. [Environment Variables](#environment-variables)
12. [AI Assistance Disclosure](#ai-assistance-disclosure)
13. [Dependencies & Licences](#dependencies--licences)

---

## Overview

The UK electricity market relies heavily on wind generation forecasts for day-ahead forward power contracts and dispatch decisions. This dashboard provides trading desks and grid analysts with actionable insight into:

- **Forecast Magnitude Accuracy:** Half-hourly MAE and RMSE across custom date ranges (focused on January 2026).
- **Directional Bias:** Signed Mean Forecast Error (MW) quantifying over-forecasting vs under-forecasting tendencies.
- **Strict Cutoff Enforcement:** Guarantees no lookahead bias by restricting forecast candidate pools strictly to runs published before the decision cutoff (default: **10:00 UTC on $D-1$**).
- **Transparent Data Lineage:** Explicitly tags and alerts users if data is sourced live from Elexon BMRS or if a deterministic synthetic fallback profile is active.

### Data Sources

| Dataset | API Route | Description |
|---|---|---|
| `FUELHH` | `GET /datasets/FUELHH` | Half-hourly metered generation outturn by fuel type (national wind delivered to GB grid) |
| `WINDFOR` | `GET /datasets/WINDFOR` | Day-ahead national wind generation forecasts (unconstrained NWP-based) |

Both datasets are sourced from the **[Elexon Balancing Mechanism Reporting Service (BMRS)](https://bmrs.elexon.co.uk/)** — the authoritative real-time source for GB electricity market data. No API key is required.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Browser  →  http://localhost:3000 (Docker) or :5173 (Vite Dev)          │
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  Frontend  (React 18 + Vite, pure CSS dark design system)         │  │
│  │                                                                   │  │
│  │   App.jsx          ← Date pickers, presets, cutoff selector       │  │
│  │   MetricCard       ← MAE · RMSE · Bias · Interval Count           │  │
│  │   GenerationChart  ← Custom pure SVG dual-line: Actual vs Forecast│  │
│  │   ErrorChart       ← Custom pure SVG signed error bars (0 baseline│  │
│  │   InsightsPanel    ← Engineering analysis of UK wind bias factors │  │
│  │   IntervalsTable   ← Search · Client pagination · CSV export      │  │
│  └──────────────────────────────┬────────────────────────────────────┘  │
│                                 │ /api/* (Dev Proxy / Nginx Proxy)      │
└─────────────────────────────────┼───────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Backend  (FastAPI + Uvicorn, Python 3.12)   :8000                      │
│                                                                         │
│   GET /api/actuals     → elexon_client → FUELHH (WIND filter)           │
│   GET /api/forecasts   → elexon_client → WINDFOR                        │
│   GET /api/accuracy    → accuracy_service (10:00 UTC D-1 decision gate) │
│   GET /api/health      → diagnostic operational status & configuration  │
│   GET /docs            → OpenAPI / Swagger UI interactive documentation │
│                                                                         │
│   Elexon Insights API  ──────────────────────────────────────────►      │
│   (Automatic 6-day chunking, deterministic fallback when offline)       │
└─────────────────────────────────────────────────────────────────────────┘
```

### Technology Choices

| Layer | Technology | Reason |
|---|---|---|
| Backend framework | FastAPI | Async-native, automatic OpenAPI documentation, strict Pydantic V2 typing |
| HTTP client | httpx | Async HTTP client supporting configurable timeouts and connection limits |
| Data validation | Pydantic V2 | Strict type validation and schema serialization |
| Frontend | React 18 + Vite | Fast Hot-Module Replacement (HMR), small bundle footprint |
| Charts | Pure SVG | Zero external dependencies (avoids bundle bloat from heavy charting libs) |
| Production serving | Nginx | High-performance static bundle serving + `/api` reverse proxy |
| Containerisation | Docker + Docker Compose | Single-command reproducible build and execution |

---

## Project Structure

```text
wind-forecast-dashboard/
├── docker-compose.yml          ← Orchestrates backend (:8000) and frontend (:3000)
├── .env.example                ← Comprehensive environment variables template
├── .gitignore                  ← Git tracking exclusions
├── README.md                   ← Architecture and operations documentation
├── FINAL_COMPLETION_REPORT.md  ← Full verification and audit findings report
│
├── backend/
│   ├── Dockerfile              ← Python 3.12-slim production container
│   ├── requirements.txt        ← Backend dependencies
│   ├── pytest.ini              ← Test discovery configuration
│   └── app/
│       ├── __init__.py
│       ├── main.py             ← FastAPI application and CORS configuration
│       ├── config.py           ← Centralized environment-driven settings
│       ├── api/
│       │   ├── actuals.py      ← GET /api/actuals
│       │   ├── forecasts.py    ← GET /api/forecasts
│       │   └── accuracy.py     ← GET /api/accuracy
│       ├── services/
│       │   ├── elexon_client.py    ← FUELHH & WINDFOR chunked fetcher
│       │   ├── accuracy_service.py ← MAE, RMSE, Bias, and decision cutoff matching
│       │   └── forecast_service.py ← Cutoff-based candidate selection
│       └── schemas/
│           └── generation.py   ← Pydantic V2 request & response schemas
│   └── tests/
│       ├── test_forecast_and_accuracy.py  ← 11 unit tests (math, cutoffs, corruption)
│       └── test_api_endpoints.py          ← 9 integration tests (FastAPI routes)
│
└── frontend/
    ├── Dockerfile              ← Multi-stage build (Node 20 → Nginx 1.27 Alpine)
    ├── nginx.conf              ← Reverse proxy (/api → backend) + SPA fallback
    ├── vercel.json             ← Single-page application routing for Vercel
    ├── vite.config.js          ← Dev proxy (/api → localhost:8000)
    ├── package.json
    └── src/
        ├── App.jsx             ← Primary dashboard container & query state
        ├── index.css           ← Dark slate design system and responsive styles
        ├── main.jsx
        └── components/
            ├── MetricCard.jsx      ← KPI summary cards
            ├── GenerationChart.jsx ← SVG dual-line generation comparison
            ├── ErrorChart.jsx      ← SVG signed error distribution bars
            ├── InsightsPanel.jsx   ← Engineering commentary on market bias
            └── IntervalsTable.jsx  ← Settlement interval audit table + CSV export
```

---

## Setup — Local Development

### Prerequisites

- Python **3.12+**
- Node.js **18+** and npm

### 1. Clone & Configure

```bash
git clone <repository-url>
cd wind-forecast-dashboard
cp .env.example .env
```

### 2. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

# Install dependencies
pip install -r requirements.txt

# Start backend server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
- API Base: `http://127.0.0.1:8000`
- Interactive Swagger UI: `http://127.0.0.1:8000/docs`
- Health Check: `http://127.0.0.1:8000/api/health`

### 3. Frontend Setup

Open a separate terminal:

```bash
cd frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
```
- Dashboard UI: `http://localhost:5173`
- The Vite dev server automatically proxies `/api` requests to `http://127.0.0.1:8000`.

---

## Setup — Docker (Recommended)

Run the entire stack with single-command Docker Compose:

```bash
# Build and start services
docker compose up --build

# Or run detached in background
docker compose up -d --build
```

| Service | URL | Role |
|---|---|---|
| **Frontend** | `http://localhost:3000` | React dashboard served via Nginx reverse proxy |
| **Backend** | `http://localhost:8000` | FastAPI application server |
| **Swagger UI** | `http://localhost:8000/docs` | OpenAPI interactive documentation |

To stop containers:
```bash
docker compose down
```

---

## API Reference

### `GET /api/accuracy`
Calculates quantitative accuracy metrics across half-hourly settlement intervals.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `start_date` | `date` | `2026-01-01` | First delivery date (`YYYY-MM-DD`) |
| `end_date` | `date` | `2026-01-31` | Last delivery date (`YYYY-MM-DD`) |
| `cutoff_hour` | `int` | `10` | Day-ahead decision cutoff hour in UTC on $D-1$ |
| `allow_fallback` | `bool` | `true` | Allows synthetic fallback if Elexon is unreachable |

**Response Schema (`AccuracyReportResponse`):**
```json
{
  "dataset": "FUELHH + WINDFOR",
  "data_source": "live",
  "fallback_reason": null,
  "start_date": "2026-01-01",
  "end_date": "2026-01-02",
  "decision_cutoff": "10:00 UTC on the day before delivery",
  "cutoff_hour": 10,
  "count": 96,
  "mae": 1420.35,
  "rmse": 1680.12,
  "bias": 950.40,
  "intervals": [
    {
      "startTime": "2026-01-01T00:00:00+00:00",
      "forecastPublishTime": "2025-12-31T08:30:00+00:00",
      "forecast": 12400.0,
      "actual": 11450.0,
      "error": 950.0,
      "absoluteError": 950.0
    }
  ]
}
```

### `GET /api/actuals`
Retrieves metered generation outturn records from `FUELHH`.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `from_date` | `date` | Today $- 2$ days | Delivery start date |
| `to_date` | `date` | Today | Delivery end date |
| `fuel_type` | `str` | `WIND` | Fuel category |

### `GET /api/forecasts`
Retrieves day-ahead wind generation forecasts from `WINDFOR`.

| Parameter | Type | Description |
|---|---|---|
| `from_date` | `date` | Target delivery start date |
| `to_date` | `date` | Target delivery end date |
| `cutoff_hours` | `float` | Optional lead-time filter in hours before interval |

### `GET /api/health`
Returns system status, environment mode, and configuration flags.

---

## Key Assumptions & Design Decisions

### 1. Decision Cutoff: 10:00 UTC Day-Ahead
Electricity day-ahead trading desks and dispatch planners make power purchase commitments the day before delivery. The application enforces a strict cutoff:
$$\text{Cutoff}(T_{\text{delivery}}) = (T_{\text{delivery}}.\text{date}() - 1\text{ day}) \text{ at } 10:00:00\text{ UTC}$$
Only forecasts with `publishTime <= Cutoff` are eligible. Among eligible candidates, the **latest** available forecast is selected. Intraday forecasts (e.g. 4h-ahead, 1h-ahead Gate Closure) are strictly excluded from the day-ahead benchmark to eliminate lookahead bias.

### 2. Timestamp Normalisation
Elexon `WINDFOR` payloads frequently include millisecond precision (e.g. `.246Z`), whereas `FUELHH` uses second precision (`:00Z`). All timestamps are normalised to UTC second precision (`.replace(second=0, microsecond=0)`) so half-hourly settlement intervals match accurately.

### 3. Automatic 6-Day Chunking
Elexon BMRS rejects date ranges exceeding 7 days with `HTTP 400 Bad Request`. The client automatically batches multi-week queries (such as the full month of January 2026) into sequential $\le 6$-day chunks and merges the results transparently.

---

## Data Lineage: Live vs Synthetic Fallback

The application distinguishes live data from simulated data:

1. **`live`**: Data was successfully retrieved from the official Elexon BMRS API. The frontend displays the green badge `🟢 Elexon BMRS Live API`.
2. **`synthetic`**: If the Elexon API is offline, times out, or returns 0 records, the backend generates a deterministic GB wind profile (3,000–16,000 MW range) satisfying all cutoff requirements.  
   - The API response explicitly returns `"data_source": "synthetic"` and `"fallback_reason": "..."`.
   - The frontend immediately displays an amber badge `🟠 Synthetic Fallback Profile` and renders an explicit warning banner explaining that the displayed numbers are simulated for testing/resilience.

---

## Accuracy Methodology

Given $N$ matched settlement intervals $(A_i, F_i)$:

- **MAE (Mean Absolute Error):**
  $$\text{MAE} = \frac{1}{N} \sum_{i=1}^{N} |F_i - A_i|$$
- **RMSE (Root Mean Square Error):**
  $$\text{RMSE} = \sqrt{\frac{1}{N} \sum_{i=1}^{N} (F_i - A_i)^2}$$
- **Bias (Mean Forecast Error):**
  $$\text{Bias} = \frac{1}{N} \sum_{i=1}^{N} (F_i - A_i)$$

**Sign Convention:**
- **Positive Bias ($F_i > A_i$):** Over-forecasting (forecast exceeded metered delivery).
- **Negative Bias ($F_i < A_i$):** Under-forecasting (actual generation exceeded forecast).
- All metrics are expressed in **Megawatts (MW)**.

---

## Testing

Run the automated test suite using `pytest`:

```bash
cd backend
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

pytest -v
```

### Test Suite Results: 20/20 PASSING

```text
backend/tests/test_api_endpoints.py::test_api_health_endpoint PASSED              [  5%]
backend/tests/test_api_endpoints.py::test_api_directory_endpoint PASSED           [ 10%]
backend/tests/test_api_endpoints.py::test_api_actuals_date_validation PASSED     [ 15%]
backend/tests/test_api_endpoints.py::test_api_forecasts_date_validation PASSED   [ 20%]
backend/tests/test_api_endpoints.py::test_api_accuracy_date_validation PASSED    [ 25%]
backend/tests/test_api_endpoints.py::test_api_accuracy_success_response_schema PASSED [ 30%]
backend/tests/test_api_endpoints.py::test_api_accuracy_synthetic_fallback_labeled PASSED [ 35%]
backend/tests/test_api_endpoints.py::test_api_actuals_success_response PASSED    [ 40%]
backend/tests/test_api_endpoints.py::test_api_forecasts_success_with_cutoff PASSED [ 45%]
backend/tests/test_forecast_and_accuracy.py::test_calculate_accuracy_basic PASSED [ 50%]
backend/tests/test_forecast_and_accuracy.py::test_calculate_accuracy_cutoff_strictly_enforced PASSED [ 55%]
backend/tests/test_forecast_and_accuracy.py::test_calculate_accuracy_empty_records PASSED [ 60%]
backend/tests/test_forecast_and_accuracy.py::test_calculate_accuracy_corrupt_data PASSED [ 65%]
backend/tests/test_forecast_and_accuracy.py::test_parse_datetime_subsecond_normalization PASSED [ 70%]
backend/tests/test_forecast_and_accuracy.py::test_mock_fallback_profile_generation PASSED [ 75%]
backend/tests/test_api_date_validation PASSED                                     [ 80%]
backend/tests/test_forecast_and_accuracy.py::test_bias_sign_convention_under_and_over PASSED [ 85%]
backend/tests/test_forecast_and_accuracy.py::test_forecast_duplicate_selection_latest PASSED [ 90%]
backend/tests/test_forecast_and_accuracy.py::test_configurable_cutoff_hour PASSED [ 95%]
backend/tests/test_forecast_and_accuracy.py::test_dataset_result_lineage_tracking PASSED [100%]

============================= 20 passed in 4.60s ==============================
```

---

## Environment Variables

| Variable | Default | Purpose |
|---|---|---|
| `ENV` | `development` | Environment mode (`development` or `production`) |
| `HOST` | `0.0.0.0` | Backend bind host |
| `PORT` | `8000` | Backend bind port |
| `ALLOWED_ORIGINS` | `http://localhost:5173,...` | Comma-separated CORS allowed origins |
| `ELEXON_BASE_URL` | `https://data.elexon.co.uk/bmrs/api/v1` | Official Elexon BMRS endpoint base URL |
| `ELEXON_TIMEOUT` | `20.0` | HTTP request timeout in seconds |
| `DEFAULT_CUTOFF_HOUR`| `10` | Default decision cutoff hour in UTC on $D-1$ |
| `ALLOW_SYNTHETIC_FALLBACK` | `true` | Enables offline/unreachable simulated profile |
| `VITE_API_BASE_URL` | `""` (empty) | Frontend API base (set in Vercel for separate backend) |

---

## AI Assistance Disclosure

This project was developed with the assistance of **Google Antigravity (powered by Claude Sonnet / Gemini)**.
- **AI Contributions:** Boilerplate routing, Pydantic schema migration, SVG polyline mathematics, and test scaffolding.
- **Human Author Decisions:** Enforcing the strict 10:00 UTC $D-1$ cutoff, eliminating future forecast leaks, implementing explicit data lineage labeling, diagnosing Elexon's $>7$-day query limits, and authoring domain explanations for B6 transmission boundary curtailment.

---

## Dependencies & Licences

- **Backend:** FastAPI (MIT), Uvicorn (BSD), httpx (BSD), Pydantic V2 (MIT), python-dotenv (BSD), pytest (MIT).
- **Frontend:** React 18 (MIT), React-DOM (MIT), Vite 6 (MIT).
- **Data Attribution:** Sourced from Elexon BMRS under Elexon data licensing terms.
