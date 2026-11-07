"""Notifiche Telegram (M7): riepilogo giornaliero, avvisi di guasto, anteprima delle proposte hybrid.

Configurazione in `.env` (mai nel repo, G-14):
    TELEGRAM_BOT_TOKEN   token del bot creato con @BotFather
    TELEGRAM_CHAT_ID     la tua chat (si trova con `money notify setup` dopo aver scritto /start al bot)
Senza queste variabili le notifiche vengono semplicemente saltate.
"""

from __future__ import annotations

import html
import os
import tomllib
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
import psycopg

from .config import REPO_ROOT

ROME = ZoneInfo("Europe/Rome")
API = "https://api.telegram.org/bot{token}/{method}"

GUARDRAIL_TEXT = {
    "G-01": "soft stop attivo",
    "G-02": "conto bloccato",
    "G-03": "vendita oltre la posizione",
    "G-04": "liquidità insufficiente",
    "G-05": "costo oltre il 2%",
    "G-06": "rendimento atteso troppo basso rispetto ai costi",
    "G-07": "troppi ordini",
    "G-08": "posizione troppo grande",
    "G-10": "dati troppo vecchi",
    "G-13": "strumento non ammesso",
}


def credentials() -> tuple[str, str] | None:
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN", ""), os.environ.get("TELEGRAM_CHAT_ID", "")
    return (token, chat) if token and chat else None


def send(text: str, client: httpx.Client | None = None, creds: tuple[str, str] | None = None) -> bool:
    """Invia un messaggio (HTML). Restituisce False se le credenziali mancano."""
    creds = creds or credentials()
    if not creds:
        return False
    token, chat = creds
    c = client or httpx.Client(timeout=20)
    r = c.post(
        API.format(token=token, method="sendMessage"),
        json={"chat_id": chat, "text": text[:4000], "parse_mode": "HTML", "disable_web_page_preview": True},
    )
    r.raise_for_status()
    return True


def discover_chat_ids(token: str, client: httpx.Client | None = None) -> list[tuple[str, str]]:
    """Chat che hanno scritto al bot (per trovare TELEGRAM_CHAT_ID)."""
    c = client or httpx.Client(timeout=20)
    r = c.get(API.format(token=token, method="getUpdates"))
    r.raise_for_status()
    out = {}
    for u in r.json().get("result", []):
        chat = (u.get("message") or u.get("my_chat_member") or {}).get("chat")
        if chat:
            out[str(chat["id"])] = chat.get("first_name") or chat.get("title") or ""
    return list(out.items())


# ───────────────────────── testo ─────────────────────────


def _eur(v) -> str:
    s = f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{s} €"


def _pct(v: float) -> str:
    return f"{v:+.2f}%".replace(".", ",")


GIORNI = ["lun", "mar", "mer", "gio", "ven", "sab", "dom"]


def _when(d: datetime) -> str:
    return f"{GIORNI[d.weekday()]} {d:%d/%m %H:%M}"


def describe(e: dict) -> str:
    k = e.get("kind")
    if k == "Fill":
        verb = "Comprate" if e["side"] == "buy" else "Vendute"
        return f"{verb} {float(e['qty']):.4f} quote di {e['instrument']} a {_eur(e['price_eur'])}"
    if k == "OrderSubmitted":
        what = _eur(e["notional_eur"]) if e.get("notional_eur") else f"{e.get('qty')} quote"
        return f"Ordine inviato: {'compra' if e['side'] == 'buy' else 'vendi'} {what} di {e['instrument']}"
    if k == "OrderRejected":
        codes = ", ".join(f"{c} ({GUARDRAIL_TEXT.get(c, '')})" for c in e["codes"])
        return f"Bloccato {e['instrument']}: {codes}"
    if k == "OrderExpired":
        return f"Ordine scaduto: {e['reason']}"
    if k == "RiskStateChanged":
        return f"⚠️ Rischio: {e['from']} → {e['to']}"
    if k == "TaxWithheld":
        return f"Imposta trattenuta: {_eur(e['amount_eur'])}"
    if k == "Interest":
        return f"Interessi: {_eur(e['amount_eur'])} lordi"
    if k == "StampDuty":
        return f"Bollo: {_eur(e['amount_eur'])}"
    if k == "Deposit":
        return f"Versamento: {_eur(e['amount_eur'])}"
    return str(k)


def hybrid_preview(order: dict, name: str, isin: str | None, ref_price: float, guard: dict, now: datetime) -> str:
    """Anteprima della notifica di una proposta hybrid (3.5): ciò che arriverebbe con i soldi veri."""
    slip = guard["hybrid"]["max_limit_slippage_pct"] / 100
    ttl = guard["hybrid"]["proposal_ttl_hours"]
    buy = order["side"] == "buy"
    max_px = ref_price * (1 + slip) if buy else ref_price * (1 - slip)
    until = (now + timedelta(hours=ttl)).astimezone(ROME)
    amount = _eur(order["notional_eur"]) if buy else f"{order['qty']} quote"
    edge = order.get("expected_edge_pct")
    lines = [
        f"{'🟢 COMPRA' if buy else '🔴 VENDI'}  {html.escape(name)}{f' ({isin})' if isin else ''}",
        f"Importo: {amount} · Prezzo {'max' if buy else 'min'} accettabile: {_eur(max_px)}"
        " (ordine a mercato frazionario)",
        f"Valida fino a: {_when(until)}",
        f"Perché: {html.escape(order.get('reason') or '—')}",
    ]
    if edge is not None:
        lines.append(f"Rendimento atteso (stima prudente): {_pct(float(edge))}")
    lines.append("[✅ Eseguito]  [⏭ Salta]  — <i>anteprima: in paper l'ordine è eseguito dal simulatore</i>")
    return "\n".join(lines)


def daily_summary(conn: psycopg.Connection, now: datetime) -> str:
    today = now.astimezone(ROME).date()
    guard = tomllib.loads((REPO_ROOT / "config" / "guardrails.toml").read_text())
    L = [f"<b>📊 Paper trading — {today:%d/%m/%Y}</b>"]

    failed = conn.execute(
        """SELECT DISTINCT ON (component) component, status, detail FROM ops.heartbeat
           WHERE (at AT TIME ZONE 'Europe/Rome')::date = %s ORDER BY component, at DESC""",
        (today,),
    ).fetchall()
    bad = [f for f in failed if f[1] not in ("ok", "running")]
    if bad:
        L.append("⚠️ <b>Problemi:</b> " + "; ".join(f"{c}: {html.escape((d or '')[:120])}" for c, _, d in bad))

    for acct, strategy in conn.execute(
        "SELECT account, strategy FROM paper.account WHERE active ORDER BY initial_deposit_eur"
    ).fetchall():
        eq = conn.execute(
            """SELECT nav_eur, net_deposits_eur, risk_state FROM paper.equity_daily WHERE account=%s
               ORDER BY date DESC LIMIT 2""",
            (acct,),
        ).fetchall()
        if not eq:
            continue
        nav, dep, risk = float(eq[0][0]), float(eq[0][1]), eq[0][2]
        diff = nav - float(eq[1][0]) if len(eq) > 1 else None
        delta = f" ({'+' if diff >= 0 else '−'}{_eur(abs(diff))} da ieri)" if diff is not None else ""
        ret = (nav / dep - 1) * 100 if dep else 0.0
        icon = {"Active": "🟢", "Suspended": "🟠", "Locked": "🔴"}.get(risk, "")
        L.append(f"\n{icon} <b>{acct}</b> · {strategy}\nValore {_eur(nav)}{delta} · {_pct(ret)} sul versato")
        events = conn.execute(
            """SELECT record->'event' FROM ledger.event WHERE account=%s
               AND ((record->>'recorded_at')::timestamptz AT TIME ZONE 'Europe/Rome')::date = %s
               AND kind NOT IN ('Deposit') ORDER BY seq""",
            (acct, today),
        ).fetchall()
        for (e,) in events:
            L.append(" • " + html.escape(describe(e)))
        if acct == "paper-50":
            for o, name, isin, px in conn.execute(
                """SELECT to_jsonb(i), r.name, r.isin, p.close_eur::float
                   FROM paper.order o JOIN paper.intent i USING (intent_id) JOIN ref.instrument r
                     ON r.instrument_id = o.instrument_id
                   JOIN LATERAL (SELECT close_eur FROM paper.price_eur WHERE instrument_id=o.instrument_id
                                 ORDER BY date DESC LIMIT 1) p ON true
                   WHERE o.account=%s AND (o.created_at AT TIME ZONE 'Europe/Rome')::date = %s""",
                (acct, today),
            ).fetchall():
                L.append("\n<b>Anteprima proposta hybrid</b>\n" + hybrid_preview(o, name, isin, px, guard, now))
    L.append("\n<i>Soldi finti: risultati simulati, non una previsione.</i>")
    return "\n".join(L)


def today_rome() -> date:
    return datetime.now(ROME).date()
