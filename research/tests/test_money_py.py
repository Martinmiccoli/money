"""Test del binding money-py: Python deve ottenere gli stessi numeri di money-core.

Si saltano se il binding non è installato (serve Rust: vedi research/README.md).
"""

import json
from decimal import Decimal
from pathlib import Path

import pytest

mp = pytest.importorskip("money_py")

REPO = Path(__file__).resolve().parents[2]


def ev(n: int, date: str, event: dict) -> str:
    ts = f"{date}T10:00:00Z"
    return json.dumps({"event_id": f"ev-{n}", "date": date, "occurred_at": ts, "recorded_at": ts, "event": event})


def fill(instr: str, side: str, qty: str, price: str, fee: str = "1") -> dict:
    return {"kind": "Fill", "instrument": instr, "side": side, "qty": qty, "price_eur": price, "commission_eur": fee}


@pytest.fixture
def ledger():
    led = mp.Ledger("paper")
    led.append(ev(1, "2026-01-05", {"kind": "Deposit", "amount_eur": "500"}))
    led.append(ev(2, "2026-01-06", fill("stock", "buy", "1", "100")))
    led.append(ev(3, "2026-02-06", fill("stock", "buy", "1", "120")))
    led.append(ev(4, "2026-03-06", fill("stock", "sell", "1", "130")))
    return led


def test_costi_trade_republic():
    tr = mp.BrokerProfile.load(str(REPO / "config/brokers/trade_republic.toml"))
    q = json.loads(tr.quote("etf_ucits", "buy", "10", "100"))
    assert Decimal(q["fill_price_eur"]) == Decimal("100.05")
    assert Decimal(q["commission_eur"]) == Decimal("1")
    assert Decimal(tr.est_side_cost_eur("etf_ucits", "buy", "50")) == Decimal("1.025")
    with pytest.raises(ValueError):
        tr.quote("azioni_marziane", "buy", "1", "1")


def test_ledger_catena_e_portafoglio(ledger):
    assert len(ledger) == 4
    records = ledger.records_json()
    mp.verify_chain(records)
    pf = json.loads(ledger.portfolio_json())
    # 500 − 101 − 121 + 129 = 407; resta 1 azione al costo medio 111.
    assert Decimal(pf["cash_eur"]) == Decimal("407")
    assert Decimal(pf["holdings"]["stock"]["cost_eur"]) == Decimal("111")
    rebuilt = mp.Ledger.from_records("paper", records)
    assert rebuilt.head_hash() == ledger.head_hash()


def test_ledger_manomesso_rilevato(ledger):
    records = json.loads(ledger.records_json())
    records[0]["event"]["amount_eur"] = "5000"
    with pytest.raises(ValueError, match="catena rotta"):
        mp.verify_chain(json.dumps(records))


def test_ledger_rifiuta_vendita_scoperta(ledger):
    with pytest.raises(ValueError, match="G-03"):
        ledger.append(ev(5, "2026-03-07", fill("stock", "sell", "5", "100")))
    assert len(ledger) == 4


def test_report_fiscale(ledger):
    rules = mp.TaxRules.load(str(REPO / "config/fisco.toml"))
    instruments = json.dumps({"stock": "RD"})
    r = json.loads(mp.tax_report(ledger.records_json(), instruments, rules, 2026))
    # Plusvalenza 129 − 111 = 18 => 26% = 4,68.
    assert Decimal(r["tax_estimated_eur"]) == Decimal("4.68")
    assert "commercialista" in r["disclaimer"]
    assert Decimal(mp.tax_due_for_last(ledger.records_json(), instruments, rules)) == Decimal("4.68")
