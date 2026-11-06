from datetime import date

import httpx
import pytest

from money_research.ingest.alpaca import AlpacaData, AlpacaError
from money_research.ingest.prices import merge_adjusted


def bar(t, c):
    return {"t": t, "o": c, "h": c + 1, "l": c - 1, "c": c, "v": 100}


def client(handler, feed="sip", keys=True):
    http = httpx.Client(base_url="https://x", transport=httpx.MockTransport(handler))
    return AlpacaData("k" if keys else "", "s" if keys else "", feed, client=http, sleep=lambda s: None)


def test_pagination_and_ny_dates():
    def handler(req):
        if "page_token" not in req.url.params:
            return httpx.Response(
                200, json={"bars": {"SPY": [bar("2026-11-02T05:00:00Z", 10)]}, "next_page_token": "p2"}
            )
        return httpx.Response(200, json={"bars": {"SPY": [bar("2026-11-03T05:00:00Z", 11)]}, "next_page_token": None})

    out = client(handler).stock_bars(["SPY"], date(2026, 11, 1))
    assert [b.date for b in out["SPY"]] == [date(2026, 11, 2), date(2026, 11, 3)]
    assert out["SPY"][0].available_at.hour == 17  # G-11


def test_retries_on_429():
    calls = {"n": 0}

    def handler(req):
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(200, json={"bars": {"SPY": [bar("2026-11-02T05:00:00Z", 10)]}})

    assert len(client(handler).stock_bars(["SPY"], date(2026, 11, 1))["SPY"]) == 1
    assert calls["n"] == 3


def test_sip_forbidden_falls_back_to_iex():
    def handler(req):
        if req.url.params["feed"] == "sip":
            return httpx.Response(403, json={"message": "subscription does not permit querying recent SIP data"})
        return httpx.Response(200, json={"bars": {"SPY": [bar("2026-11-02T05:00:00Z", 10)]}})

    c = client(handler)
    assert len(c.stock_bars(["SPY"], date(2026, 11, 1))["SPY"]) == 1
    assert c.feed == "iex"


def test_errors_are_raised_and_keys_required():
    with pytest.raises(AlpacaError):
        client(lambda r: httpx.Response(500, text="boom"), feed="iex").stock_bars(["SPY"], date(2026, 1, 1))
    with pytest.raises(AlpacaError):
        client(lambda r: httpx.Response(200), keys=False).stock_bars(["SPY"], date(2026, 1, 1))


def test_crypto_works_without_keys():
    def handler(req):
        assert "APCA-API-KEY-ID" not in req.headers
        return httpx.Response(200, json={"bars": {"BTC/USD": [bar("2020-01-01T00:00:00Z", 7000)]}})

    out = client(handler, keys=False).crypto_bars(["BTC/USD"], date(2020, 1, 1))
    assert out["BTC/USD"][0].date == date(2020, 1, 1)


def test_merge_adjusted_by_date():
    from money_research.ingest.alpaca import _parse_bars

    raw = _parse_bars("SPY", [bar("2026-11-02T05:00:00Z", 10), bar("2026-11-03T05:00:00Z", 11)], False)
    adj = _parse_bars("SPY", [bar("2026-11-03T05:00:00Z", 10.5)], False)
    assert [a for _, a in merge_adjusted(raw, adj)] == [None, 10.5]
