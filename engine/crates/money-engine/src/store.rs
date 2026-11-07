//! Accesso a Postgres: ledger, feed dei prezzi, intenzioni, ordini, equity, heartbeat.

use std::collections::{BTreeMap, HashMap};

use anyhow::{anyhow, Context, Result};
use chrono::{DateTime, NaiveDate, Utc};
use money_core::{
    ledger::{Ledger, Record},
    tax::TaxCategory,
    types::{AssetClass, Side},
};
use postgres::{Client, NoTls, Transaction};
use rust_decimal::Decimal;

use crate::plan::{AccountCfg, Bar, EquityRow, Feed, Instrument, Intent, PendingOrder};

pub fn connect(url: &str) -> Result<Client> {
    Client::connect(url, NoTls).context("connessione al database")
}

fn side(s: &str) -> Result<Side> {
    match s {
        "buy" => Ok(Side::Buy),
        "sell" => Ok(Side::Sell),
        _ => Err(anyhow!("side non valido: {s}")),
    }
}

pub fn side_str(s: Side) -> &'static str {
    match s {
        Side::Buy => "buy",
        Side::Sell => "sell",
    }
}

pub fn accounts(c: &mut Client) -> Result<Vec<AccountCfg>> {
    Ok(c
        .query(
            "SELECT account, initial_deposit_eur, monthly_deposit_eur, started_on FROM paper.account WHERE active ORDER BY account",
            &[],
        )?
        .iter()
        .map(|r| AccountCfg {
            id: r.get(0),
            initial_deposit: r.get(1),
            monthly_deposit: r.get(2),
            started_on: r.get(3),
        })
        .collect())
}

pub fn instruments(c: &mut Client) -> Result<BTreeMap<String, Instrument>> {
    let mut out = BTreeMap::new();
    for r in c.query(
        "SELECT instrument_id, asset_class, tax_category FROM ref.instrument",
        &[],
    )? {
        let ac: String = r.get(1);
        let tc: Option<String> = r.get(2);
        let asset_class: AssetClass = serde_json::from_value(serde_json::Value::String(ac.clone()))
            .map_err(|_| anyhow!("asset_class sconosciuta: {ac}"))?;
        let Some(tc) = tc else { continue };
        let tax_category: TaxCategory =
            serde_json::from_value(serde_json::Value::String(tc.clone()))
                .map_err(|_| anyhow!("tax_category sconosciuta: {tc}"))?;
        out.insert(
            r.get(0),
            Instrument {
                asset_class,
                tax_category,
            },
        );
    }
    Ok(out)
}

pub fn feed(c: &mut Client) -> Result<Feed> {
    let mut map: HashMap<String, Vec<Bar>> = HashMap::new();
    for r in c.query(
        "SELECT instrument_id, date, open_eur, close_eur, available_at FROM paper.price_eur ORDER BY instrument_id, date",
        &[],
    )? {
        map.entry(r.get(0)).or_default().push(Bar {
            date: r.get(1),
            open: r.get(2),
            close: r.get(3),
            available_at: r.get(4),
        });
    }
    Ok(Feed(map))
}

pub fn rates(c: &mut Client) -> Result<Vec<(NaiveDate, f64)>> {
    Ok(c.query(
        "SELECT date, rate_pct FROM market.rate_1d WHERE series='ESTR' ORDER BY date",
        &[],
    )?
    .iter()
    .map(|r| (r.get(0), r.get(1)))
    .collect())
}

pub fn ledger(c: &mut Client, account: &str) -> Result<Ledger> {
    let rows = c.query(
        "SELECT record FROM ledger.event WHERE account=$1 ORDER BY seq",
        &[&account],
    )?;
    let records: Vec<Record> = rows
        .iter()
        .map(|r| serde_json::from_value(r.get::<_, serde_json::Value>(0)))
        .collect::<Result<_, _>>()
        .context("record del ledger non leggibile")?;
    Ledger::from_records(account, records).map_err(|e| anyhow!("ledger di {account}: {e}"))
}

/// Scrive i record nuovi (da `from` in poi). Il trigger del DB ricontrolla l'aggancio della catena.
pub fn append_records(tx: &mut Transaction, ledger: &Ledger, from: usize) -> Result<usize> {
    let new = &ledger.records()[from..];
    for r in new {
        tx.execute(
            "INSERT INTO ledger.event (account, seq, event_id, kind, date, occurred_at, record, prev_hash, hash)
             VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)",
            &[
                &r.account,
                &(r.seq as i64),
                &r.event_id,
                &r.event.kind(),
                &r.date,
                &r.occurred_at,
                &serde_json::to_value(r)?,
                &r.prev_hash,
                &r.hash,
            ],
        )?;
    }
    Ok(new.len())
}

pub fn pending_orders(c: &mut Client, account: &str) -> Result<Vec<PendingOrder>> {
    c.query(
        "SELECT order_id, instrument_id, side, notional_eur, qty, order_kind, exec_date
         FROM paper.order WHERE account=$1 AND status='pending' ORDER BY exec_date, order_id",
        &[&account],
    )?
    .iter()
    .map(|r| {
        Ok(PendingOrder {
            order_id: r.get(0),
            instrument: r.get(1),
            side: side(r.get(2))?,
            notional_eur: r.get(3),
            qty: r.get(4),
            order_kind: r.get(5),
            exec_date: r.get(6),
        })
    })
    .collect()
}

pub fn new_intents(c: &mut Client, account: &str) -> Result<Vec<Intent>> {
    c.query(
        "SELECT intent_id, instrument_id, side, notional_eur, qty, order_kind, expected_edge_pct, reason
         FROM paper.intent WHERE account=$1 AND status='new' ORDER BY intent_id",
        &[&account],
    )?
    .iter()
    .map(|r| {
        Ok(Intent {
            intent_id: r.get(0),
            instrument: r.get(1),
            side: side(r.get(2))?,
            notional_eur: r.get(3),
            qty: r.get(4),
            order_kind: r.get(5),
            expected_edge_pct: r.get(6),
            reason: r.get(7),
        })
    })
    .collect()
}

pub fn equity_history(c: &mut Client, account: &str) -> Result<Vec<EquityRow>> {
    Ok(c
        .query(
            "SELECT date, nav_eur, cash_eur, invested_eur, net_deposits_eur, high_water_mark_eur, risk_state
             FROM paper.equity_daily WHERE account=$1 ORDER BY date",
            &[&account],
        )?
        .iter()
        .map(|r| EquityRow {
            date: r.get(0),
            nav: r.get(1),
            cash: r.get(2),
            invested: r.get(3),
            net_deposits: r.get(4),
            hwm: r.get(5),
            risk_state: r.get(6),
        })
        .collect())
}

pub fn save_equity(tx: &mut Transaction, account: &str, e: &EquityRow) -> Result<()> {
    tx.execute(
        "INSERT INTO paper.equity_daily (account, date, nav_eur, cash_eur, invested_eur, net_deposits_eur,
                                         high_water_mark_eur, risk_state)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8)
         ON CONFLICT (account, date) DO UPDATE SET nav_eur=EXCLUDED.nav_eur, cash_eur=EXCLUDED.cash_eur,
            invested_eur=EXCLUDED.invested_eur, net_deposits_eur=EXCLUDED.net_deposits_eur,
            high_water_mark_eur=EXCLUDED.high_water_mark_eur, risk_state=EXCLUDED.risk_state, computed_at=now()",
        &[&account, &e.date, &e.nav, &e.cash, &e.invested, &e.net_deposits, &e.hwm, &e.risk_state],
    )?;
    Ok(())
}

pub fn mark_order(
    tx: &mut Transaction,
    order_id: &str,
    status: &str,
    fill: Option<serde_json::Value>,
) -> Result<()> {
    tx.execute(
        "UPDATE paper.order SET status=$2, settled_at=now(), fill=$3 WHERE order_id=$1",
        &[&order_id, &status, &fill],
    )?;
    Ok(())
}

pub fn insert_order(
    tx: &mut Transaction,
    account: &str,
    intent_id: i64,
    o: &PendingOrder,
) -> Result<()> {
    tx.execute(
        "INSERT INTO paper.order (order_id, account, intent_id, instrument_id, side, notional_eur, qty, order_kind, exec_date)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)",
        &[
            &o.order_id,
            &account,
            &intent_id,
            &o.instrument,
            &side_str(o.side),
            &o.notional_eur,
            &o.qty,
            &o.order_kind,
            &o.exec_date,
        ],
    )?;
    Ok(())
}

pub fn mark_intent(tx: &mut Transaction, intent_id: i64, status: &str) -> Result<()> {
    tx.execute(
        "UPDATE paper.intent SET status=$2, processed_at=now() WHERE intent_id=$1",
        &[&intent_id, &status],
    )?;
    Ok(())
}

pub fn heartbeat(c: &mut Client, component: &str, status: &str, detail: &str) -> Result<()> {
    c.execute(
        "INSERT INTO ops.heartbeat (component, status, detail) VALUES ($1,$2,$3)",
        &[&component, &status, &detail],
    )?;
    Ok(())
}

// ───────────────────────── Alpaca ombra ─────────────────────────

pub fn proxy_symbol(c: &mut Client, instrument: &str) -> Result<Option<String>> {
    Ok(c
        .query_opt(
            "SELECT source_symbol FROM ref.instrument_map WHERE instrument_id=$1 AND source IN ('alpaca_stock','alpaca_crypto')",
            &[&instrument],
        )?
        .map(|r| r.get(0)))
}

pub fn last_eurusd(c: &mut Client) -> Result<Option<f64>> {
    Ok(c.query_opt(
        "SELECT rate FROM market.fx_1d WHERE pair='EURUSD' ORDER BY date DESC LIMIT 1",
        &[],
    )?
    .map(|r| r.get(0)))
}

#[allow(clippy::too_many_arguments)]
pub fn insert_shadow(
    c: &mut Client,
    order_id: &str,
    alpaca_id: Option<&str>,
    symbol: &str,
    side: &str,
    notional_usd: Decimal,
    status: &str,
    detail: Option<&str>,
) -> Result<()> {
    c.execute(
        "INSERT INTO paper.alpaca_shadow (order_id, alpaca_order_id, symbol, side, notional_usd, status, detail)
         VALUES ($1,$2,$3,$4,$5,$6,$7) ON CONFLICT (order_id) DO NOTHING",
        &[&order_id, &alpaca_id, &symbol, &side, &notional_usd, &status, &detail],
    )?;
    Ok(())
}

pub fn open_shadows(c: &mut Client) -> Result<Vec<(String, String)>> {
    Ok(c
        .query(
            "SELECT order_id, alpaca_order_id FROM paper.alpaca_shadow
             WHERE alpaca_order_id IS NOT NULL AND status NOT IN ('filled','canceled','expired','rejected')",
            &[],
        )?
        .iter()
        .map(|r| (r.get(0), r.get(1)))
        .collect())
}

pub fn update_shadow(
    c: &mut Client,
    order_id: &str,
    status: &str,
    price: Option<Decimal>,
    filled_at: Option<DateTime<Utc>>,
) -> Result<()> {
    c.execute(
        "UPDATE paper.alpaca_shadow SET status=$2, filled_avg_price_usd=$3, filled_at=$4 WHERE order_id=$1",
        &[&order_id, &status, &price, &filled_at],
    )?;
    Ok(())
}
