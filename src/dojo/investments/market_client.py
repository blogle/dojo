"""Market data access wrapper for investment tracking.

This module isolates all yfinance/pandas usage so the rest of the system can
operate on plain Python types and database rows.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from typing import Any

import pandas as pd
import yfinance as yf

EXPECTED_PRICE_COLUMNS = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]


class MarketClient:
    """Fetch and normalize daily OHLC market data via Yahoo Finance."""

    def __init__(self, *, max_workers: int = 8) -> None:
        self._max_workers = max_workers

    def fetch_prices(self, tickers: list[str], start_date: date) -> dict[str, pd.DataFrame]:
        """Fetch daily OHLC data for tickers starting at start_date.

        Returns a dict keyed by *normalized* uppercase ticker.
        Each DataFrame is normalized to:
          - a daily DateTimeIndex (including non-trading days as NaNs)
          - the expected columns in EXPECTED_PRICE_COLUMNS
        """

        normalized = [t.strip().upper() for t in tickers if t and t.strip()]
        if not normalized:
            return {}

        max_workers = min(self._max_workers, len(normalized))
        results: dict[str, pd.DataFrame] = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(self._fetch_single_ticker, ticker, start_date): ticker for ticker in normalized}
            for future in as_completed(futures):
                ticker = futures[future]
                df = future.result()
                results[ticker] = self._normalize_prices_frame(df)
        return results

    def fetch_metadata(self, ticker: str) -> dict[str, Any]:
        """Fetch best-effort metadata for a ticker."""

        info: dict[str, Any] = {}
        try:
            raw = yf.Ticker(ticker.strip().upper()).info
            if isinstance(raw, dict):
                info = raw
        except Exception:
            # yfinance can raise for invalid tickers or transient network errors.
            return {}

        name = info.get("shortName") or info.get("longName") or info.get("displayName")
        quote_type = info.get("quoteType")
        currency = info.get("currency")
        return {
            "name": name,
            "quote_type": quote_type,
            "currency": currency,
        }

    def _fetch_single_ticker(self, ticker: str, start_date: date) -> pd.DataFrame:
        # yfinance is blocking; this method is designed to run in threadpool.
        return yf.Ticker(ticker).history(start=start_date, interval="1d", auto_adjust=False)

    def _normalize_prices_frame(self, df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            out = pd.DataFrame(columns=pd.Index(EXPECTED_PRICE_COLUMNS))
            out.index.name = "market_date"
            return out

        df = df.copy()

        # Normalize index to midnight UTC-less datetime.
        if not isinstance(df.index, pd.DatetimeIndex):
            df.index = pd.to_datetime(df.index)
        if df.index.tz is not None:
            df.index = df.index.tz_convert(None)
        df.index = pd.DatetimeIndex(df.index.values.astype("datetime64[D]"))
        df.index.name = "market_date"

        # Normalize column names (case-insensitive match into expected set).
        lowered = {str(col).lower(): col for col in df.columns}
        normalized_cols: dict[str, str] = {}
        for expected in EXPECTED_PRICE_COLUMNS:
            key = expected.lower()
            actual = lowered.get(key)
            if actual is None:
                # yfinance uses "Adj Close" spelling; handle missing gracefully.
                normalized_cols[expected] = expected
                continue
            normalized_cols[expected] = actual

        out = pd.DataFrame(index=df.index)
        for expected in EXPECTED_PRICE_COLUMNS:
            actual = normalized_cols[expected]
            if actual in df.columns:
                out[expected] = df[actual]
            else:
                out[expected] = pd.NA

        # Ensure a dense daily index from first to last observed date.
        start = out.index.min()
        end = out.index.max()
        if start is not pd.NaT and end is not pd.NaT:
            out = out.reindex(pd.date_range(start=start, end=end, freq="D"), copy=False)
            out.index.name = "market_date"

        return out
