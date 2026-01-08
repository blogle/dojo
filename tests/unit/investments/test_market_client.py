from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from dojo.investments.market_client import EXPECTED_PRICE_COLUMNS, MarketClient


class _FakeTicker:
    def __init__(self, ticker: str, frames: dict[str, pd.DataFrame]) -> None:
        self._ticker = ticker
        self._frames = frames

    def history(self, *, start: date, interval: str, auto_adjust: bool) -> pd.DataFrame:
        _ = (start, interval, auto_adjust)
        return self._frames[self._ticker]


class _FakeYFinance:
    def __init__(self, frames: dict[str, pd.DataFrame]) -> None:
        self._frames = frames

    def Ticker(self, ticker: str) -> _FakeTicker:  # noqa: N802 (yfinance API)
        return _FakeTicker(ticker, self._frames)


def test_fetch_prices_normalizes_multiple_tickers(monkeypatch: pytest.MonkeyPatch) -> None:
    frames = {
        "AAPL": pd.DataFrame(
            {
                "Open": [10.0, 11.0],
                "High": [10.5, 11.5],
                "Low": [9.5, 10.5],
                "Close": [10.2, 11.2],
                "Adj Close": [10.1, 11.1],
                "Volume": [100, 200],
            },
            index=pd.to_datetime(["2025-01-02", "2025-01-04"]),
        ),
        "MSFT": pd.DataFrame(
            {
                "Close": [50.0],
            },
            index=pd.to_datetime(["2025-02-01"]),
        ),
    }

    import dojo.investments.market_client as market_client_module

    monkeypatch.setattr(market_client_module, "yf", _FakeYFinance(frames))

    client = MarketClient(max_workers=2)
    out = client.fetch_prices(["aapl", "msft"], start_date=date(2025, 1, 1))

    assert set(out.keys()) == {"AAPL", "MSFT"}

    aapl = out["AAPL"]
    assert list(aapl.columns) == EXPECTED_PRICE_COLUMNS
    # Should be reindexed to daily (includes 2025-01-03).
    assert pd.Timestamp("2025-01-03") in aapl.index

    msft = out["MSFT"]
    assert list(msft.columns) == EXPECTED_PRICE_COLUMNS


def test_fetch_prices_handles_missing_fields_and_nans(monkeypatch: pytest.MonkeyPatch) -> None:
    frames = {
        "AAPL": pd.DataFrame(
            {
                "Close": [float("nan"), 100.0],
                "Volume": [float("nan"), 123.0],
            },
            index=pd.to_datetime(["2025-03-01", "2025-03-02"]),
        )
    }

    import dojo.investments.market_client as market_client_module

    monkeypatch.setattr(market_client_module, "yf", _FakeYFinance(frames))

    client = MarketClient(max_workers=1)
    out = client.fetch_prices(["AAPL"], start_date=date(2025, 3, 1))

    df = out["AAPL"]
    assert list(df.columns) == EXPECTED_PRICE_COLUMNS
    # Missing OHLC columns are present and filled with NA.
    assert df["Open"].isna().all()
    assert df["High"].isna().all()
    assert df["Low"].isna().all()


def test_fetch_prices_empty_ticker_list_is_noop() -> None:
    client = MarketClient()
    assert client.fetch_prices([], start_date=date(2025, 1, 1)) == {}
