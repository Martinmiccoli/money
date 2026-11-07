//! Logica pura di una giornata di paper trading: nessun I/O, testabile.
//!
//! - [`settle`]: esegue gli ordini in attesa al prezzo di apertura (SimBroker), poi versamenti,
//!   interessi sulla liquidità e bollo.
//! - [`execute`]: controlla le intenzioni d'ordine con i guardrails e le trasforma in ordini;
//!   valuta il conto alla chiusura e aggiorna la macchina del rischio.
//!
//! Le regole sono le stesse del simulatore di backtest (`research/.../simulator.py`).

use std::collections::{BTreeMap, HashMap};

use anyhow::{anyhow, Result};
use chrono::{DateTime, Datelike, Duration, NaiveDate, Timelike, Utc, Weekday};
use chrono_tz::Europe::Rome;
use money_core::{
    config::GuardrailsConfig,
    costs::{BrokerProfile, OrderKind},
    guardrails::{self, CheckedOrder},
    ledger::{Event, Ledger, NewEvent},
    risk::{RiskEvent, RiskMachine, RiskState},
    tax::{self, TaxCategory, TaxRules},
    types::{AssetClass, OrderRequest, PortfolioSnapshot, Position, Side},
};
use rust_decimal::{prelude::ToPrimitive, Decimal, RoundingStrategy};
use serde::{Deserialize, Serialize};

const QTY_DP: u32 = 6;
const EXPIRE_AFTER_DAYS: i64 = 5;

#[derive(Debug, Clone)]
pub struct Bar {
    pub date: NaiveDate,
    pub open: Decimal,
    pub close: Decimal,
    pub available_at: DateTime<Utc>,
}

/// Prezzi EUR del paper (`paper.price_eur`), per strumento e in ordine di data.
#[derive(Debug, Clone, Default)]
pub struct Feed(pub HashMap<String, Vec<Bar>>);

impl Feed {
    pub fn bar_on(&self, inst: &str, d: NaiveDate) -> Option<&Bar> {
        self.0.get(inst)?.iter().find(|b| b.date == d)
    }

    /// Ultima barra pubblicata prima di `now` (G-11).
    pub fn last_available(&self, inst: &str, now: DateTime<Utc>) -> Option<&Bar> {
        self.0
            .get(inst)?
            .iter()
            .rev()
            .find(|b| b.available_at < now)
    }

    pub fn close_asof(&self, inst: &str, d: NaiveDate) -> Option<Decimal> {
        self.0
            .get(inst)?
            .iter()
            .rev()
            .find(|b| b.date <= d)
            .map(|b| b.close)
    }
}

#[derive(Debug, Clone, Copy)]
pub struct Instrument {
    pub asset_class: AssetClass,
    pub tax_category: TaxCategory,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct PendingOrder {
    pub order_id: String,
    pub instrument: String,
    pub side: Side,
    pub notional_eur: Option<Decimal>,
    pub qty: Option<Decimal>,
    pub order_kind: String,
    pub exec_date: NaiveDate,
}

#[derive(Debug, Clone)]
pub struct Intent {
    pub intent_id: i64,
    pub instrument: String,
    pub side: Side,
    pub notional_eur: Option<Decimal>,
    pub qty: Option<Decimal>,
    pub order_kind: String,
    pub expected_edge_pct: Option<Decimal>,
    pub reason: String,
}

#[derive(Debug, Clone, PartialEq)]
pub struct EquityRow {
    pub date: NaiveDate,
    pub nav: Decimal,
    pub cash: Decimal,
    pub invested: Decimal,
    pub net_deposits: Decimal,
    pub hwm: f64,
    pub risk_state: String,
}

#[derive(Debug, Clone)]
pub struct AccountCfg {
    pub id: String,
    pub initial_deposit: Decimal,
    pub monthly_deposit: Decimal,
    pub started_on: NaiveDate,
}

/// Tutto ciò che serve per pianificare una giornata.
pub struct Ctx<'a> {
    pub broker: &'a BrokerProfile,
    pub rules: &'a TaxRules,
    pub guard: &'a GuardrailsConfig,
    pub instruments: &'a BTreeMap<String, Instrument>,
    pub feed: &'a Feed,
    /// €STR: (data, tasso % annuo), in ordine di data.
    pub rates: &'a [(NaiveDate, f64)],
    pub now: DateTime<Utc>,
}

impl Ctx<'_> {
    pub fn today(&self) -> NaiveDate {
        self.now.with_timezone(&Rome).date_naive()
    }

    fn categories(&self) -> BTreeMap<String, TaxCategory> {
        self.instruments
            .iter()
            .map(|(k, v)| (k.clone(), v.tax_category))
            .collect()
    }

    fn instrument(&self, id: &str) -> Result<Instrument> {
        self.instruments
            .get(id)
            .copied()
            .ok_or_else(|| anyhow!("strumento sconosciuto: {id} (manca in ref.instrument)"))
    }

    fn rate_pct(&self, d: NaiveDate) -> f64 {
        self.rates
            .iter()
            .rev()
            .find(|(rd, _)| *rd < d)
            .map_or(0.0, |(_, r)| *r)
    }
}

fn push(ledger: &mut Ledger, ctx: &Ctx, date: NaiveDate, event: Event) -> Result<()> {
    let date = ledger.records().last().map_or(date, |r| r.date.max(date));
    let id = format!("{}-{}", ledger.account(), ledger.records().len() + 1);
    ledger.append(NewEvent {
        event_id: id,
        date,
        occurred_at: ctx.now,
        recorded_at: ctx.now,
        event,
    })?;
    Ok(())
}

fn kind_of(s: &str) -> OrderKind {
    if s == "savings_plan" {
        OrderKind::SavingsPlan
    } else {
        OrderKind::Regular
    }
}

fn floor_qty(q: Decimal) -> Decimal {
    q.round_dp_with_strategy(QTY_DP, RoundingStrategy::ToZero)
}

/// Esito di un ordine in attesa.
#[derive(Debug, Clone, PartialEq)]
pub enum Settlement {
    Filled(serde_json::Value),
    Expired(String),
    Waiting,
}

/// Esecuzione SimBroker degli ordini in attesa, poi eventi di cassa programmati.
pub fn settle(
    ledger: &mut Ledger,
    ctx: &Ctx,
    acct: &AccountCfg,
    pending: &[PendingOrder],
    equity_hist: &[EquityRow],
) -> Result<Vec<(String, Settlement)>> {
    let today = ctx.today();
    let mut out = Vec::new();
    let mut sorted: Vec<&PendingOrder> = pending.iter().collect();
    sorted.sort_by_key(|o| (o.exec_date, o.order_id.clone()));
    for o in sorted {
        let s = settle_one(ledger, ctx, o)?;
        let s = match s {
            Settlement::Waiting if (today - o.exec_date).num_days() > EXPIRE_AFTER_DAYS => {
                let reason = "nessuna quotazione entro 5 giorni".to_string();
                push(
                    ledger,
                    ctx,
                    today,
                    Event::OrderExpired {
                        order_id: o.order_id.clone(),
                        reason: reason.clone(),
                    },
                )?;
                Settlement::Expired(reason)
            }
            other => other,
        };
        out.push((o.order_id.clone(), s));
    }
    // Gli eventi di cassa si registrano solo a ordini chiusi, così le date restano in ordine.
    if out.iter().any(|(_, s)| *s == Settlement::Waiting) {
        return Ok(out);
    }
    cash_events(ledger, ctx, acct, equity_hist)?;
    Ok(out)
}

fn settle_one(ledger: &mut Ledger, ctx: &Ctx, o: &PendingOrder) -> Result<Settlement> {
    let Some(bar) = ctx
        .feed
        .bar_on(&o.instrument, o.exec_date)
        .filter(|b| b.available_at <= ctx.now)
    else {
        return Ok(Settlement::Waiting);
    };
    let inst = ctx.instrument(&o.instrument)?;
    let kind = kind_of(&o.order_kind);
    let held = ledger
        .portfolio()
        .holdings
        .get(&o.instrument)
        .map_or(Decimal::ZERO, |h| h.qty);
    let qty = match o.side {
        Side::Buy => {
            let unit = ctx.broker.quote(
                inst.asset_class,
                Side::Buy,
                kind,
                Decimal::ONE,
                bar.open,
                false,
            )?;
            let budget = o.notional_eur.unwrap_or_default() - unit.commission_eur;
            floor_qty(budget / unit.fill_price_eur)
        }
        Side::Sell => {
            let q = o
                .qty
                .unwrap_or_else(|| o.notional_eur.unwrap_or_default() / bar.open);
            floor_qty(q.min(held))
        }
    };
    if qty <= Decimal::ZERO {
        let reason = "quantità nulla all'esecuzione".to_string();
        push(
            ledger,
            ctx,
            o.exec_date,
            Event::OrderExpired {
                order_id: o.order_id.clone(),
                reason: reason.clone(),
            },
        )?;
        return Ok(Settlement::Expired(reason));
    }
    let q = ctx
        .broker
        .quote(inst.asset_class, o.side, kind, qty, bar.open, false)?;
    let fill = Event::Fill {
        instrument: o.instrument.clone(),
        side: o.side,
        qty,
        price_eur: q.fill_price_eur,
        commission_eur: q.commission_eur,
        transaction_tax_eur: q.ftt_eur,
        ref_price_eur: Some(bar.open),
        venue: Some("SimBroker".into()),
        broker_order_id: Some(o.order_id.clone()),
        settlement_date: None,
        white_list_pct: None,
    };
    if let Err(e) = push(ledger, ctx, o.exec_date, fill) {
        let reason = format!("esecuzione rifiutata dal ledger: {e}");
        push(
            ledger,
            ctx,
            o.exec_date,
            Event::OrderExpired {
                order_id: o.order_id.clone(),
                reason: reason.clone(),
            },
        )?;
        return Ok(Settlement::Expired(reason));
    }
    let mut tax_withheld = Decimal::ZERO;
    if o.side == Side::Sell {
        tax_withheld = tax::tax_due_for_last(ledger.records(), ctx.rules, &ctx.categories())?;
        if tax_withheld > Decimal::ZERO {
            push(
                ledger,
                ctx,
                o.exec_date,
                Event::TaxWithheld {
                    amount_eur: tax_withheld,
                    reference: Some(o.order_id.clone()),
                },
            )?;
        }
    }
    Ok(Settlement::Filled(serde_json::json!({
        "date": o.exec_date,
        "qty": qty,
        "price_eur": q.fill_price_eur,
        "ref_open_eur": bar.open,
        "commission_eur": q.commission_eur,
        "spread_cost_eur": q.spread_cost_eur,
        "tax_withheld_eur": tax_withheld,
    })))
}

fn month_start(d: NaiveDate) -> NaiveDate {
    NaiveDate::from_ymd_opt(d.year(), d.month(), 1).expect("data valida")
}

/// Versamenti, interessi del mese precedente e bollo dell'anno precedente.
fn cash_events(
    ledger: &mut Ledger,
    ctx: &Ctx,
    acct: &AccountCfg,
    hist: &[EquityRow],
) -> Result<()> {
    let today = ctx.today();
    let has = |ledger: &Ledger, pred: &dyn Fn(&Event, NaiveDate) -> bool| {
        ledger.records().iter().any(|r| pred(&r.event, r.date))
    };

    // Versamento iniziale e mensile.
    if !has(ledger, &|e, _| matches!(e, Event::Deposit { .. })) {
        push(
            ledger,
            ctx,
            today,
            Event::Deposit {
                amount_eur: acct.initial_deposit,
            },
        )?;
    } else if acct.monthly_deposit > Decimal::ZERO
        && !has(ledger, &|e, d| {
            matches!(e, Event::Deposit { .. }) && month_start(d) == month_start(today)
        })
    {
        push(
            ledger,
            ctx,
            today,
            Event::Deposit {
                amount_eur: acct.monthly_deposit,
            },
        )?;
    }

    // Interessi del mese precedente (€STR se positivo, come nel backtest), con ritenuta del 26%.
    let this_month = month_start(today);
    let prev_month = month_start(this_month - Duration::days(1));
    let credited = has(ledger, &|e, d| {
        matches!(e, Event::Interest { .. }) && month_start(d) == this_month
    });
    if !credited && prev_month >= month_start(acct.started_on) {
        let rows: Vec<&EquityRow> = hist
            .iter()
            .filter(|r| month_start(r.date) == prev_month)
            .collect();
        let mut accrued = 0.0;
        for (i, r) in rows.iter().enumerate() {
            let next = rows.get(i + 1).map_or(this_month, |n| n.date);
            let cash = r.cash.to_f64().unwrap_or(0.0).max(0.0);
            accrued += cash * ctx.rate_pct(r.date).max(0.0) / 100.0
                * (next - r.date).num_days() as f64
                / 365.0;
        }
        let amount = Decimal::try_from(accrued)
            .unwrap_or_default()
            .round_dp_with_strategy(2, RoundingStrategy::ToZero);
        if amount > Decimal::ZERO {
            push(ledger, ctx, today, Event::Interest { amount_eur: amount })?;
            let tax_due = tax::tax_due_for_last(ledger.records(), ctx.rules, &ctx.categories())?;
            if tax_due > Decimal::ZERO {
                push(
                    ledger,
                    ctx,
                    today,
                    Event::TaxWithheld {
                        amount_eur: tax_due,
                        reference: Some("interessi".into()),
                    },
                )?;
            }
        }
    }

    // Bollo dell'anno precedente, giorno per giorno sul valore investito.
    let year = today.year();
    let charged = has(ledger, &|e, d| {
        matches!(e, Event::StampDuty { .. }) && d.year() == year
    });
    if !charged && acct.started_on.year() < year {
        let rows: Vec<&EquityRow> = hist.iter().filter(|r| r.date.year() == year - 1).collect();
        let year_end = NaiveDate::from_ymd_opt(year, 1, 1).expect("data valida");
        let mut daily = Vec::new();
        for (i, r) in rows.iter().enumerate() {
            let next = rows.get(i + 1).map_or(year_end, |n| n.date);
            let mut d = r.date;
            while d < next {
                daily.push((d, r.invested));
                d += Duration::days(1);
            }
        }
        let amount = tax::stamp_duty_estimate(ctx.rules, &daily);
        if amount > Decimal::ZERO {
            push(ledger, ctx, today, Event::StampDuty { amount_eur: amount })?;
        }
    }
    Ok(())
}

/// Giorno di esecuzione: oggi se è feriale e la borsa USA non ha ancora aperto (15:30 a Roma),
/// altrimenti il prossimo giorno feriale.
pub fn exec_date(now: DateTime<Utc>) -> NaiveDate {
    let local = now.with_timezone(&Rome);
    let mut d = local.date_naive();
    if local.hour() >= 15 {
        d += Duration::days(1);
    }
    while matches!(d.weekday(), Weekday::Sat | Weekday::Sun) {
        d += Duration::days(1);
    }
    d
}

/// Esito di un'intenzione d'ordine.
#[derive(Debug)]
pub enum IntentOutcome {
    Rejected {
        codes: Vec<String>,
        detail: String,
    },
    Submitted {
        order: PendingOrder,
        checked: CheckedOrder,
    },
}

fn to_f64(d: Decimal) -> f64 {
    d.to_f64().unwrap_or(f64::NAN)
}

fn risk_state(s: &str) -> RiskState {
    match s {
        "Suspended" => RiskState::Suspended,
        "Locked" => RiskState::Locked,
        _ => RiskState::Active,
    }
}

/// Controlla ogni intenzione con i guardrails e crea gli ordini per il SimBroker.
pub fn execute(
    ledger: &mut Ledger,
    ctx: &Ctx,
    intents: &[Intent],
    last_equity: Option<&EquityRow>,
) -> Result<Vec<(i64, IntentOutcome)>> {
    let today = ctx.today();
    let state = last_equity.map_or(RiskState::Active, |e| risk_state(&e.risk_state));
    let mut out = Vec::new();
    for it in intents {
        let outcome = execute_one(ledger, ctx, it, state, today)?;
        match &outcome {
            IntentOutcome::Rejected { codes, detail } => push(
                ledger,
                ctx,
                today,
                Event::OrderRejected {
                    instrument: it.instrument.clone(),
                    side: it.side,
                    codes: codes.clone(),
                    detail: detail.clone(),
                },
            )?,
            IntentOutcome::Submitted { order, .. } => push(
                ledger,
                ctx,
                today,
                Event::OrderSubmitted {
                    order_id: order.order_id.clone(),
                    instrument: order.instrument.clone(),
                    side: order.side,
                    notional_eur: order.notional_eur,
                    qty: order.qty,
                    order_kind: order.order_kind.clone(),
                    adapter: "SimBroker".into(),
                    expected_edge_pct: it.expected_edge_pct,
                    reason: it.reason.clone(),
                },
            )?,
        }
        out.push((it.intent_id, outcome));
    }
    Ok(out)
}

fn execute_one(
    ledger: &Ledger,
    ctx: &Ctx,
    it: &Intent,
    state: RiskState,
    today: NaiveDate,
) -> Result<IntentOutcome> {
    let rejected = |code: &str, detail: String| IntentOutcome::Rejected {
        codes: vec![code.into()],
        detail,
    };
    let inst = ctx.instrument(&it.instrument)?;
    let Some(ref_bar) = ctx.feed.last_available(&it.instrument, ctx.now) else {
        // nessun dato disponibile = dato infinitamente vecchio (G-10)
        return Ok(rejected(
            "G-10",
            "nessun prezzo disponibile alla decisione".into(),
        ));
    };
    let px = ref_bar.close;
    let pf = ledger.portfolio();

    // Fotografia del portafoglio ai prezzi noti alla decisione.
    let mut positions = HashMap::new();
    let mut ages = vec![(ctx.now - ref_bar.available_at).num_seconds() as f64 / 3600.0];
    let mut invested = Decimal::ZERO;
    for (id, h) in &pf.holdings {
        let bar = ctx.feed.last_available(id, ctx.now);
        let value = bar.map_or(Decimal::ZERO, |b| b.close * h.qty);
        ages.push(bar.map_or(1e9, |b| {
            (ctx.now - b.available_at).num_seconds() as f64 / 3600.0
        }));
        invested += value;
        positions.insert(
            id.clone(),
            Position {
                asset_class: ctx.instrument(id)?.asset_class,
                value_eur: to_f64(value),
            },
        );
    }
    let week = today.iso_week();
    let submitted: Vec<NaiveDate> = ledger
        .records()
        .iter()
        .filter(|r| matches!(r.event, Event::OrderSubmitted { .. }))
        .map(|r| r.date)
        .collect();
    let snapshot = PortfolioSnapshot {
        equity_eur: to_f64(pf.cash_eur + invested),
        cash_eur: to_f64(pf.cash_eur),
        positions,
        orders_today: submitted.iter().filter(|d| **d == today).count() as u32,
        orders_this_week: submitted.iter().filter(|d| d.iso_week() == week).count() as u32,
        data_age_hours: ages.into_iter().fold(0.0, f64::max).min(1e9),
    };

    // Quantità stimata al prezzo di riferimento (come nel backtest).
    let kind = kind_of(&it.order_kind);
    let held = pf
        .holdings
        .get(&it.instrument)
        .map_or(Decimal::ZERO, |h| h.qty);
    let qty = match it.side {
        Side::Buy => {
            let unit =
                ctx.broker
                    .quote(inst.asset_class, Side::Buy, kind, Decimal::ONE, px, false)?;
            floor_qty(
                (it.notional_eur.unwrap_or_default() - unit.commission_eur) / unit.fill_price_eur,
            )
        }
        Side::Sell => floor_qty(
            it.qty
                .unwrap_or_else(|| it.notional_eur.unwrap_or_default() / px)
                .min(held),
        ),
    };
    if qty <= Decimal::ZERO {
        return Ok(rejected("QTY", "quantità nulla".into()));
    }
    let q = ctx
        .broker
        .quote(inst.asset_class, it.side, kind, qty, px, false)?;
    let order = OrderRequest {
        instrument: it.instrument.clone(),
        asset_class: inst.asset_class,
        side: it.side,
        notional_eur: to_f64(qty * px),
        est_cost_eur: to_f64(q.total_cost_eur()),
        expected_edge_pct: it.expected_edge_pct.map(to_f64),
        ref_price: to_f64(px),
        limit_price: None,
        valid_for_hours: None,
    };
    match guardrails::check(ctx.guard, state, &snapshot, order) {
        Err(v) => Ok(IntentOutcome::Rejected {
            codes: v.iter().map(|x| x.code().to_string()).collect(),
            detail: v
                .iter()
                .map(|x| x.to_string())
                .collect::<Vec<_>>()
                .join("; "),
        }),
        Ok(checked) => Ok(IntentOutcome::Submitted {
            order: PendingOrder {
                order_id: format!("{}-i{}", ledger.account(), it.intent_id),
                instrument: it.instrument.clone(),
                side: it.side,
                notional_eur: if it.side == Side::Buy {
                    it.notional_eur
                } else {
                    None
                },
                qty: if it.side == Side::Sell {
                    Some(qty)
                } else {
                    None
                },
                order_kind: it.order_kind.clone(),
                exec_date: exec_date(ctx.now),
            },
            checked,
        }),
    }
}

/// Valutazione alla chiusura più recente disponibile e aggiornamento del rischio (G-01/G-02).
pub fn valuate(
    ledger: &mut Ledger,
    ctx: &Ctx,
    last_equity: Option<&EquityRow>,
) -> Result<(EquityRow, Option<RiskEvent>)> {
    let pf = ledger.portfolio().clone();
    let date = ctx
        .feed
        .0
        .values()
        .filter_map(|bars| bars.iter().rev().find(|b| b.available_at < ctx.now))
        .map(|b| b.date)
        .max()
        .unwrap_or_else(|| ctx.today());
    let mut invested = Decimal::ZERO;
    for (id, h) in &pf.holdings {
        let px = ctx
            .feed
            .close_asof(id, date)
            .ok_or_else(|| anyhow!("nessun prezzo per {id} al {date}"))?;
        invested += px * h.qty;
    }
    let nav = pf.cash_eur + invested;
    let mut cfg = ctx.guard.clone();
    cfg.capital.net_deposits_eur = to_f64(pf.net_deposits_eur).max(0.01);
    let mut rm = match last_equity {
        Some(e) => RiskMachine::restore(risk_state(&e.risk_state), e.hwm),
        None => RiskMachine::new(to_f64(nav)),
    };
    let before = rm.state();
    let event = rm.update(&cfg, to_f64(nav));
    if let Some(ev) = &event {
        push(
            ledger,
            ctx,
            ctx.today(),
            Event::RiskStateChanged {
                from: format!("{before:?}"),
                to: format!("{:?}", rm.state()),
                equity_eur: nav.round_dp(2),
                detail: format!("{ev:?}"),
            },
        )?;
    }
    Ok((
        EquityRow {
            date,
            nav: nav.round_dp(8),
            cash: pf.cash_eur,
            invested: invested.round_dp(8),
            net_deposits: pf.net_deposits_eur,
            hwm: rm.high_water_mark_eur(),
            risk_state: format!("{:?}", rm.state()),
        },
        event,
    ))
}
