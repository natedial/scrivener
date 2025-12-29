# Scrivener

Economic and markets data sourcing platform.

Scrivener collects, normalizes, and serves economic and financial market data from free public APIs (FRED, BLS, Treasury). It provides a unified interface for querying time series data and Treasury auction results.

## Features

- **Multi-source data collection**: FRED (31 series), BLS (10+ series), Treasury auctions
- **Automated scheduling**: Daily sweeps + calendar-driven fetches for economic releases
- **Query layer**: SeriesQuery and AuctionQuery utilities for data access
- **REST API**: FastAPI service with auto-generated docs
- **CLI**: Full management interface for manual operations

## Quick Start

### Installation

```bash
# Clone and setup
cd scrivener
python3.11 -m venv venv
source venv/bin/activate
pip install -e .
```

### Configuration

Create a `.env` file:

```bash
# Database (Supabase session pooler)
DATABASE_URL=postgresql://user:password@host:5432/postgres

# API Keys
FRED_API_KEY=your-fred-api-key
BLS_API_KEY=your-bls-api-key  # Optional

# Scheduler (defaults shown)
DEFAULT_LOOKBACK_YEARS=5
DAILY_SWEEP_HOUR=17
DAILY_SWEEP_MINUTE=0
TIMEZONE=America/New_York
```

### Initialize Database

```bash
scrivener init-db
```

### Fetch Data

```bash
# Fetch a single series
scrivener fetch fred GDP

# Fetch all core series for a source
scrivener fetch-core fred

# Run a full sweep
scrivener sweep all
```

### Query Data

```bash
# Get latest value
scrivener query FEDFUNDS --latest

# Get time series
scrivener query GDP --days 365

# Query auctions
scrivener query-auctions --summary
scrivener query-auctions --type Note --days 60
```

### Start Services

```bash
# Start the scheduler
scrivener scheduler

# Start the API server
scrivener serve --port 8000
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `init-db` | Initialize database schema |
| `fetch <source> <series>` | Fetch single series |
| `fetch-core <source>` | Fetch all core series |
| `list-series <source>` | List available core series |
| `sweep [source]` | Run immediate sweep (fred/bls/all) |
| `scheduler` | Start the scheduler daemon |
| `config` | Show current configuration |
| `query <series_id>` | Query time series data |
| `query-auctions` | Query Treasury auction data |
| `auctions` | Fetch Treasury auction data |
| `upcoming-auctions` | Show upcoming Treasury auctions |
| `releases` | List known economic release types |
| `upcoming` | Show upcoming economic events |
| `serve` | Start the API server |

## API Endpoints

When running `scrivener serve`, the following endpoints are available:

### Series
- `GET /series` - List all series
- `GET /series/search?q=...` - Search series
- `GET /series/{id}` - Get series metadata
- `GET /series/{id}/latest` - Get latest value
- `GET /series/{id}/observations` - Get time series
- `GET /series/{id}/change` - Calculate period change
- `POST /series/batch/latest` - Get multiple latest values

### Auctions
- `GET /auctions` - Get recent auctions
- `GET /auctions/summary` - Get aggregate statistics
- `GET /auctions/cusip/{cusip}` - Get by CUSIP
- `GET /auctions/yields/{type}/{term}` - Get yield history
- `GET /auctions/latest/{type}/{term}` - Get latest for type/term

### Health
- `GET /health` - Health check

API documentation available at `/docs` when the server is running.

## Data Sources

### FRED (31 core series)
- GDP & Growth: GDP, GDPC1, A191RL1Q225SBEA
- Inflation: CPIAUCSL, CPILFESL, PCEPI, PCEPILFE
- Employment: UNRATE, PAYEMS, ICSA, CCSA, JTSJOL
- Interest Rates: FEDFUNDS, DFEDTARU, DFEDTARL, SOFR
- Treasury Yields: Full curve (DGS1MO through DGS30)
- Markets: SP500, VIXCLS, DTWEXBGS

### BLS
- Unemployment: LNS14000000
- Employment: CES0000000001
- CPI: CUSR0000SA0, CUSR0000SA0L1E
- PPI: WPUFD4

### Treasury
- Auction results (Bills, Notes, Bonds, TIPS, FRN)
- Upcoming auctions

## Scheduler

The scheduler runs two types of jobs:

1. **Daily Sweep** (5pm ET): Fetches all core series from all sources
2. **Calendar Check** (6am & 6pm ET): Checks `economic_events` table and schedules fetches for upcoming releases

Event-triggered fetches run 1 minute after the scheduled release time.

## Project Structure

```
scrivener/
├── src/
│   ├── cli.py           # CLI commands
│   ├── config.py        # Configuration
│   ├── db/              # Database models and connection
│   ├── fetchers/        # Data source fetchers
│   ├── scheduler/       # APScheduler jobs and runner
│   ├── query/           # Query utilities
│   └── api/             # FastAPI service
├── migrations/          # SQL migrations
├── pyproject.toml
└── requirements.txt
```

## Requirements

- Python 3.11+
- PostgreSQL (Supabase recommended)
- FRED API key (free at https://fred.stlouisfed.org/docs/api/api_key.html)
- BLS API key (optional, increases rate limits)

## License

MIT
