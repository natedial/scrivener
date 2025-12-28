# Scrivener: Economic & Markets Data Platform

## Overview

Scrivener is a data sourcing and management platform that collects, normalizes, and serves economic and financial market data. It serves as the foundational data layer for downstream tools and agents.

---

## Tech Stack

### Core Components

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **Data Collection** | Python 3.11+ | Rich ecosystem (pandas, requests, httpx), best library support for FRED/BLS APIs |
| **Data Pipeline** | Go (future) | High-performance processing when scale demands it |
| **Database** | PostgreSQL (Supabase) | Managed, user-friendly, built-in REST API, good free tier |
| **Task Scheduling** | APScheduler / Celery | Python-native, handles cron-like jobs for data fetches |
| **Caching** | Redis (optional) | For hot data paths when latency matters |
| **API Layer** | FastAPI | Async, auto-docs, excellent performance for Python |

### Python Dependencies (Initial)

```
httpx              # Async HTTP client
pandas             # Data manipulation
sqlalchemy         # ORM / raw SQL
psycopg2-binary    # PostgreSQL driver
pydantic           # Data validation
fredapi            # Official FRED API wrapper
apscheduler        # Job scheduling
python-dotenv      # Environment management
```

---

## Data Sources (Free Tier)

### Tier 1: Official APIs (Highest Priority)

| Source | Data | API | Rate Limits | Notes |
|--------|------|-----|-------------|-------|
| **FRED** | Macro indicators, rates, GDP, inflation | REST | 120 req/min | Best single source for macro data |
| **BLS** | Employment, CPI, PPI, wages | REST | 500 req/day (unregistered), more with key | Primary labor market source |
| **Treasury** | Yields, auction data | REST | Generous | treasury.gov/resource-center/data-chart-center |
| **SEC EDGAR** | Corporate filings | REST | 10 req/sec | Company fundamentals |

### Tier 2: Supplementary APIs

| Source | Data | Notes |
|--------|------|-------|
| **Census Bureau** | Economic indicators, trade data | api.census.gov |
| **DOL** | Unemployment claims, OEWS | developer.dol.gov |
| **World Bank** | International macro | api.worldbank.org |
| **Yahoo Finance** | Market prices (unofficial) | yfinance library (use carefully, ToS gray area) |
| **Alpha Vantage** | Markets (free tier limited) | 5 calls/min, 500/day |

### Tier 3: Scraping (Last Resort)

For data without stable APIs:
- BLS release schedules/calendars
- Fed meeting minutes/statements
- Treasury auction announcements

**Scraping principles:**
- Cache aggressively
- Respect robots.txt
- Rate limit strictly
- Build fallbacks

---

## Database Schema Design

### Core Principles

1. **Normalize series metadata** - Store series info once, observations separately
2. **Temporal consistency** - All timestamps in UTC, with release dates tracked
3. **Source tracking** - Know where every data point came from
4. **Revision handling** - Economic data gets revised; track versions

### Initial Schema

```sql
-- Data sources registry
CREATE TABLE sources (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,      -- 'FRED', 'BLS', 'TREASURY'
    base_url TEXT,
    rate_limit_per_min INT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Series metadata
CREATE TABLE series (
    id SERIAL PRIMARY KEY,
    source_id INT REFERENCES sources(id),
    external_id VARCHAR(100) NOT NULL,     -- 'GDP', 'UNRATE', etc.
    name TEXT NOT NULL,
    description TEXT,
    frequency VARCHAR(20),                  -- 'daily', 'weekly', 'monthly', 'quarterly'
    units VARCHAR(100),
    seasonal_adjustment VARCHAR(20),
    last_updated TIMESTAMPTZ,
    metadata JSONB,                         -- Flexible additional fields
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source_id, external_id)
);

-- Time series observations
CREATE TABLE observations (
    id BIGSERIAL PRIMARY KEY,
    series_id INT REFERENCES series(id),
    date DATE NOT NULL,
    value NUMERIC,
    release_date TIMESTAMPTZ,              -- When this value was released
    revision_num INT DEFAULT 0,            -- Track revisions
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(series_id, date, revision_num)
);

-- Index for fast time-range queries
CREATE INDEX idx_observations_series_date ON observations(series_id, date DESC);
CREATE INDEX idx_observations_release ON observations(release_date DESC);

-- Data fetch job tracking
CREATE TABLE fetch_jobs (
    id SERIAL PRIMARY KEY,
    source_id INT REFERENCES sources(id),
    series_ids INT[],                      -- Which series this job updates
    schedule VARCHAR(50),                  -- Cron expression
    last_run TIMESTAMPTZ,
    last_status VARCHAR(20),
    next_run TIMESTAMPTZ,
    config JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Audit log for debugging
CREATE TABLE fetch_logs (
    id BIGSERIAL PRIMARY KEY,
    job_id INT REFERENCES fetch_jobs(id),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    status VARCHAR(20),
    records_fetched INT,
    records_inserted INT,
    error_message TEXT
);

-- Economic release calendar for scheduled fetches
CREATE TABLE release_calendar (
    id SERIAL PRIMARY KEY,
    release_name VARCHAR(100) NOT NULL,     -- 'CPI', 'NFP', 'FOMC'
    source_id INT REFERENCES sources(id),
    series_ids INT[],                        -- Which series this release affects
    scheduled_time TIMESTAMPTZ NOT NULL,     -- When the release is scheduled
    actual_time TIMESTAMPTZ,                 -- When it actually released (if different)
    status VARCHAR(20) DEFAULT 'pending',    -- 'pending', 'released', 'delayed'
    fetch_triggered_at TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_release_calendar_scheduled ON release_calendar(scheduled_time);
CREATE INDEX idx_release_calendar_status ON release_calendar(status) WHERE status = 'pending';
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        SCRIVENER                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Fetchers   │  │   Fetchers   │  │   Scrapers   │          │
│  │   (FRED)     │  │   (BLS)      │  │   (misc)     │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                   │
│         └─────────────────┼─────────────────┘                   │
│                           ▼                                     │
│                  ┌─────────────────┐                            │
│                  │   Normalizer    │  ← Transforms to common    │
│                  │   / Validator   │    schema, validates       │
│                  └────────┬────────┘                            │
│                           │                                     │
│                           ▼                                     │
│                  ┌─────────────────┐                            │
│                  │   PostgreSQL    │  ← Supabase                │
│                  │   (Supabase)    │                            │
│                  └────────┬────────┘                            │
│                           │                                     │
│         ┌─────────────────┼─────────────────┐                   │
│         │                 │                 │                   │
│         ▼                 ▼                 ▼                   │
│  ┌────────────┐   ┌────────────┐   ┌────────────┐              │
│  │  PostgREST │   │  FastAPI   │   │   Direct   │              │
│  │  (built-in)│   │  (custom)  │   │   SQL      │              │
│  └────────────┘   └────────────┘   └────────────┘              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  Other Tools /  │
                    │     Agents      │
                    └─────────────────┘
```

---

## Project Phases

### Phase 1: Foundation (Current)

**Goal:** Basic infrastructure, first data source working end-to-end

- [ ] Set up project structure
- [ ] Configure Supabase project + connection
- [ ] Implement database schema
- [ ] Build FRED fetcher (highest value, most comprehensive)
- [ ] Create base fetcher class with common logic
- [ ] Basic CLI for manual data pulls
- [ ] Logging and error handling

**Key series to start with (FRED):**
- `GDP` - Gross Domestic Product
- `UNRATE` - Unemployment Rate
- `CPIAUCSL` - Consumer Price Index
- `FEDFUNDS` - Federal Funds Rate
- `DGS10` - 10-Year Treasury Yield
- `SP500` - S&P 500 Index

### Phase 2: Expand Sources

**Goal:** Add BLS, Treasury, basic scheduling

- [ ] BLS API integration
- [ ] Treasury data integration
- [ ] APScheduler for automated fetches
- [ ] Series dependency tracking (e.g., real GDP needs deflator)
- [ ] Basic data quality checks

### Phase 3: API Layer

**Goal:** Make data accessible to other tools

- [ ] FastAPI service with key endpoints
- [ ] Query interface: by series, date range, latest
- [ ] Aggregation endpoints (% change, moving averages)
- [ ] Authentication for external access
- [ ] Rate limiting

### Phase 4: Real-time & Reliability

**Goal:** Near-real-time data access, production hardening

- [ ] BLS release calendar monitoring
- [ ] Webhook/polling for new releases
- [ ] Redis caching for hot paths
- [ ] Alerting on fetch failures
- [ ] Data freshness monitoring
- [ ] Revision tracking and alerts

### Phase 5: High-Performance Pipeline (Future)

**Goal:** Go-based pipeline for latency-critical paths

- [ ] Identify bottlenecks requiring Go rewrite
- [ ] Implement Go data pipeline components
- [ ] Benchmark and optimize

---

## Directory Structure

```
scrivener/
├── src/
│   ├── __init__.py
│   ├── config.py              # Configuration management
│   ├── db/
│   │   ├── __init__.py
│   │   ├── connection.py      # Database connection handling
│   │   ├── models.py          # SQLAlchemy models
│   │   └── migrations/        # Schema migrations
│   ├── fetchers/
│   │   ├── __init__.py
│   │   ├── base.py            # Base fetcher class
│   │   ├── fred.py            # FRED API fetcher
│   │   ├── bls.py             # BLS API fetcher
│   │   └── treasury.py        # Treasury data fetcher
│   ├── scrapers/
│   │   ├── __init__.py
│   │   └── base.py            # Base scraper class
│   ├── normalizers/
│   │   ├── __init__.py
│   │   └── base.py            # Data normalization logic
│   ├── scheduler/
│   │   ├── __init__.py
│   │   └── jobs.py            # Scheduled job definitions
│   └── api/
│       ├── __init__.py
│       ├── main.py            # FastAPI app
│       └── routes/
├── tests/
│   ├── __init__.py
│   ├── test_fetchers/
│   └── test_api/
├── scripts/
│   └── seed_series.py         # Initial series setup
├── .env.example
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## Key Considerations

### Accuracy

- **Source of truth:** Always prefer official government sources
- **Revision tracking:** Economic data is revised; store revision history
- **Validation:** Sanity checks on fetched data (null checks, range validation)
- **Audit trail:** Log every fetch operation

### Latency

- **Caching strategy:** Redis for frequently accessed series
- **Connection pooling:** Supabase provides this, but configure appropriately
- **Batch operations:** Insert in batches, not row-by-row
- **Indexed queries:** Ensure proper indexes on series_id, date

### Reliability

- **Retry logic:** Exponential backoff for failed fetches
- **Circuit breakers:** Don't hammer failing APIs
- **Graceful degradation:** Serve stale data if fresh unavailable
- **Monitoring:** Track fetch success rates, data freshness

### Cost (Free Tier Limits)

| Service | Free Tier | Strategy |
|---------|-----------|----------|
| Supabase | 500MB DB, 2GB bandwidth | Start here, monitor usage |
| FRED | 120 req/min | More than enough for daily fetches |
| BLS | 500 req/day (unregistered) | Get API key for more |
| Alpha Vantage | 5 req/min, 500/day | Use sparingly for market data |

---

## Immediate Next Steps

1. **Create Supabase project** - Set up database, get connection string
2. **Initialize Python project** - pyproject.toml, dependencies
3. **Implement schema** - Run migrations on Supabase
4. **Build FRED fetcher** - End-to-end working example
5. **Test with 5-10 key series** - Validate data flow

---

## Decisions Made

| Decision | Choice | Notes |
|----------|--------|-------|
| **Historical depth** | 5 years initial | Schema supports fetching further back without overwriting |
| **Update frequency** | Daily sweep at 5pm ET + calendar-driven | Scheduled pulls for sensitive releases (CPI, NFP, etc.) |
| **Market data** | Delayed feeds acceptable | Multiple sources needed for fixed income coverage |
| **Supabase region** | AWS us-east-1 | Aligns with other infrastructure |

---

## Fixed Income Data Sources

US fixed income is a priority. Free/delayed options:

| Source | Data Available | Limitations |
|--------|----------------|-------------|
| **FRED** | Treasury yields (DGS1-DGS30), SOFR, Fed Funds, swap rates | Daily, no intraday |
| **Treasury Direct** | Auction results, daily yield curves | Official source, daily |
| **Nasdaq Data Link** (Quandl) | Some free bond datasets | Limited free tier |
| **Yahoo Finance** | Bond ETF prices (TLT, IEF, SHY as proxies) | ToS concerns, delayed |
| **Investing.com** | Rates futures (scraping) | Requires scraping, fragile |

**Rates futures challenge:** CME protects futures data aggressively. For free tier:
- Use underlying rates from FRED as primary (Fed Funds, SOFR, Treasury yields)
- Bond ETFs as market sentiment proxies
- Consider paid data later for actual futures prices

---

## Economic Calendar & Scheduled Releases

Key releases requiring calendar-driven fetches:

| Release | Source | Typical Time (ET) | Frequency |
|---------|--------|-------------------|-----------|
| CPI | BLS | 8:30 AM | Monthly |
| PPI | BLS | 8:30 AM | Monthly |
| Employment (NFP) | BLS | 8:30 AM | Monthly (1st Friday) |
| JOLTS | BLS | 10:00 AM | Monthly |
| GDP | BEA/FRED | 8:30 AM | Quarterly |
| PCE | BEA/FRED | 8:30 AM | Monthly |
| FOMC Decision | Fed | 2:00 PM | ~8x/year |
| Initial Claims | DOL | 8:30 AM | Weekly (Thursday) |

**Implementation approach:**
1. Maintain release calendar table in DB
2. Scheduler checks calendar daily, queues jobs for next day's releases
3. Jobs trigger ~1 min after scheduled release time
4. Retry logic for delayed releases
