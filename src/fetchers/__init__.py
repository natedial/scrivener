"""Data fetchers for various sources."""

from src.fetchers.base import BaseFetcher
from src.fetchers.bls import BlsFetcher
from src.fetchers.fred import FredFetcher

__all__ = ["BaseFetcher", "BlsFetcher", "FredFetcher"]
