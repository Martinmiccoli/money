from datetime import date

import httpx

from money_research.ingest.ecb import fetch_eur_rates, parse_ecb_csv

CSV = """KEY,FREQ,CURRENCY,CURRENCY_DENOM,EXR_TYPE,EXR_SUFFIX,TIME_PERIOD,OBS_VALUE,OBS_STATUS
EXR.D.USD.EUR.SP00.A,D,USD,EUR,SP00,A,2026-11-02,1.1523,A
EXR.D.USD.EUR.SP00.A,D,USD,EUR,SP00,A,2026-11-03,,
EXR.D.USD.EUR.SP00.A,D,USD,EUR,SP00,A,2026-11-04,1.1490,A
"""


def test_parse_skips_missing_values():
    rates = parse_ecb_csv(CSV, "EURUSD")
    assert [(r.date, r.rate) for r in rates] == [(date(2026, 11, 2), 1.1523), (date(2026, 11, 4), 1.1490)]
    # G-11: disponibile dalle 17:00 di Francoforte del giorno stesso
    assert rates[0].available_at.hour == 17


def test_fetch_uses_start_and_handles_404():
    seen = {}

    def handler(req: httpx.Request):
        seen["start"] = req.url.params["startPeriod"]
        return httpx.Response(404 if seen["start"] == "2099-01-01" else 200, text=CSV)

    c = httpx.Client(transport=httpx.MockTransport(handler))
    assert len(fetch_eur_rates("USD", date(2026, 11, 1), c)) == 2
    assert seen["start"] == "2026-11-01"
    assert fetch_eur_rates("USD", date(2099, 1, 1), c) == []
