"""FRED (Federal Reserve Economic Data) fetcher."""

import logging
from datetime import date
from typing import Any

from fredapi import Fred

from src.fetchers.base import BaseFetcher

logger = logging.getLogger(__name__)


# Key FRED series for initial setup
CORE_SERIES = {
    # GDP & Growth
    "GDP": "Gross Domestic Product",
    "GDPC1": "Real Gross Domestic Product",
    "A191RL1Q225SBEA": "Real GDP Growth Rate",
    # Inflation
    "CPIAUCSL": "Consumer Price Index for All Urban Consumers",
    "CPILFESL": "Core CPI (Less Food and Energy)",
    "PCEPI": "Personal Consumption Expenditures Price Index",
    "PCEPILFE": "Core PCE Price Index",
    # Employment
    "UNRATE": "Unemployment Rate",
    "PAYEMS": "Total Nonfarm Payrolls",
    "ICSA": "Initial Jobless Claims",
    "CCSA": "Continued Claims",
    "JTSJOL": "Job Openings (JOLTS)",
    # Interest Rates
    "FEDFUNDS": "Federal Funds Effective Rate",
    "DFEDTARU": "Federal Funds Target Rate Upper",
    "DFEDTARL": "Federal Funds Target Rate Lower",
    "SOFR": "Secured Overnight Financing Rate",
    # Treasury Yields
    "DGS1MO": "1-Month Treasury",
    "DGS3MO": "3-Month Treasury",
    "DGS6MO": "6-Month Treasury",
    "DGS1": "1-Year Treasury",
    "DGS2": "2-Year Treasury",
    "DGS5": "5-Year Treasury",
    "DGS7": "7-Year Treasury",
    "DGS10": "10-Year Treasury",
    "DGS20": "20-Year Treasury",
    "DGS30": "30-Year Treasury",
    # Spreads
    "T10Y2Y": "10-Year Treasury Minus 2-Year Treasury",
    "T10Y3M": "10-Year Treasury Minus 3-Month Treasury",
    # Other
    "SP500": "S&P 500 Index",
    "DTWEXBGS": "Trade Weighted US Dollar Index",
    "VIXCLS": "CBOE Volatility Index (VIX)",
}


class FredFetcher(BaseFetcher):
    """Fetcher for FRED (Federal Reserve Economic Data)."""

    source_name = "FRED"
    base_url = "https://api.stlouisfed.org/fred"
    rate_limit_per_min = 120

    def __init__(self) -> None:
        super().__init__()
        if not self.settings.fred_api_key:
            raise ValueError("FRED_API_KEY is required. Get one at https://fred.stlouisfed.org/docs/api/api_key.html")
        self._client = Fred(api_key=self.settings.fred_api_key)

    def fetch_series_info(self, external_id: str) -> dict[str, Any]:
        """Fetch series metadata from FRED."""
        info = self._client.get_series_info(external_id)

        # Map FRED frequency codes to human-readable
        freq_map = {
            "D": "daily",
            "W": "weekly",
            "BW": "biweekly",
            "M": "monthly",
            "Q": "quarterly",
            "SA": "semiannual",
            "A": "annual",
        }

        return {
            "name": info.get("title", external_id),
            "description": info.get("notes"),
            "frequency": freq_map.get(info.get("frequency_short"), info.get("frequency")),
            "units": info.get("units"),
            "seasonal_adjustment": info.get("seasonal_adjustment_short"),
            "metadata": {
                "fred_id": info.get("id"),
                "realtime_start": str(info.get("realtime_start")),
                "realtime_end": str(info.get("realtime_end")),
                "observation_start": str(info.get("observation_start")),
                "observation_end": str(info.get("observation_end")),
                "popularity": info.get("popularity"),
            },
        }

    def fetch_observations(
        self,
        external_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch observations from FRED."""
        start_date = start_date or self.get_default_start_date()
        end_date = end_date or date.today()

        # fredapi returns a pandas Series
        data = self._client.get_series(
            external_id,
            observation_start=start_date,
            observation_end=end_date,
        )

        observations = []
        for obs_date, value in data.items():
            # Skip NaN values
            if value != value:  # NaN check
                continue
            observations.append({
                "date": obs_date.date() if hasattr(obs_date, "date") else obs_date,
                "value": float(value),
            })

        return observations

    def fetch_with_revisions(
        self,
        external_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch observations with revision history (vintage dates).

        This is useful for understanding how data was revised over time.
        """
        start_date = start_date or self.get_default_start_date()
        end_date = end_date or date.today()

        # Get all vintage dates for this series
        vintages = self._client.get_series_all_releases(external_id)

        observations = []
        for _, row in vintages.iterrows():
            if row["value"] != row["value"]:  # NaN check
                continue
            obs_date = row.name
            if hasattr(obs_date, "date"):
                obs_date = obs_date.date()
            if start_date <= obs_date <= end_date:
                observations.append({
                    "date": obs_date,
                    "value": float(row["value"]),
                    "release_date": row.get("realtime_start"),
                })

        return observations

    @classmethod
    def get_core_series(cls) -> dict[str, str]:
        """Get the dictionary of core FRED series."""
        return CORE_SERIES.copy()

    def fetch_core_series(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch all core series."""
        return self.fetch_multiple(
            list(CORE_SERIES.keys()),
            start_date=start_date,
            end_date=end_date,
        )
