"""Test delle notifiche Telegram (nessuna rete: httpx MockTransport)."""

import json
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

from money_research import notify

GUARD = {"hybrid": {"max_limit_slippage_pct": 1.5, "proposal_ttl_hours": 72}}


def test_send_salta_senza_credenziali(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    assert notify.send("ciao") is False


def test_send_usa_html_e_chat():
    seen = {}

    def handler(req: httpx.Request):
        seen["url"] = str(req.url)
        seen["body"] = json.loads(req.content)
        return httpx.Response(200, json={"ok": True})

    c = httpx.Client(transport=httpx.MockTransport(handler))
    assert notify.send("<b>x</b>", client=c, creds=("TOKEN", "42"))
    assert seen["url"].endswith("/botTOKEN/sendMessage")
    assert seen["body"]["chat_id"] == "42" and seen["body"]["parse_mode"] == "HTML"


def test_scoperta_della_chat():
    updates = {"result": [{"message": {"chat": {"id": 123, "first_name": "Martin"}}}]}
    c = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=updates)))
    assert notify.discover_chat_ids("T", c) == [("123", "Martin")]


def test_anteprima_proposta_hybrid():
    now = datetime(2026, 11, 9, 9, 5, tzinfo=ZoneInfo("Europe/Rome"))
    order = {"side": "buy", "notional_eur": "52", "reason": "trend positivo", "expected_edge_pct": "4.1"}
    text = notify.hybrid_preview(order, "iShares Core MSCI World", "IE00B4L5Y983", 100.0, GUARD, now)
    assert "🟢 COMPRA  iShares Core MSCI World (IE00B4L5Y983)" in text
    assert "Importo: 52,00 €" in text
    assert "Prezzo max accettabile: 101,50 €" in text  # +1,5% (G-09)
    assert "Valida fino a: gio 12/11 09:05" in text  # +72 ore
    assert "+4,10%" in text


def test_descrizione_dei_rifiuti_spiega_il_guardrail():
    e = {"kind": "OrderRejected", "instrument": "x", "side": "buy", "codes": ["G-06"]}
    assert "rendimento atteso troppo basso" in notify.describe(e)
