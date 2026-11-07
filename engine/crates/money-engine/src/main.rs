//! CLI del motore di paper trading.
//!
//! ```text
//! money-engine settle    esegue gli ordini in attesa (SimBroker), interessi, bollo, versamenti
//! money-engine execute   guardrails sulle intenzioni → ordini; valutazione e rischio; Alpaca ombra
//! money-engine status    riepilogo dei conti
//! ```

use std::path::{Path, PathBuf};

use anyhow::{bail, Context, Result};
use chrono::{DateTime, Utc};
use clap::{Parser, Subcommand};
use money_core::{config::GuardrailsConfig, costs::BrokerProfile, tax::TaxRules, types::Mode};
use money_engine::{
    alpaca::AlpacaPaper,
    plan::{self, Ctx, IntentOutcome, Settlement},
    store,
};
use rust_decimal::Decimal;

#[derive(Parser)]
#[command(name = "money-engine", about = "Motore di paper trading (M6)")]
struct Cli {
    /// Istante della decisione (RFC 3339), per test e recuperi. Default: adesso.
    #[arg(long, global = true)]
    now: Option<DateTime<Utc>>,
    #[command(subcommand)]
    cmd: Cmd,
}

#[derive(Subcommand)]
enum Cmd {
    Settle,
    Execute,
    Status,
}

fn repo_root() -> Result<PathBuf> {
    if let Ok(p) = std::env::var("MONEY_REPO") {
        return Ok(PathBuf::from(p));
    }
    let mut d = std::env::current_dir()?;
    loop {
        if d.join("config/guardrails.toml").exists() {
            return Ok(d);
        }
        if !d.pop() {
            bail!("radice del repo non trovata (imposta MONEY_REPO)");
        }
    }
}

struct Setup {
    guard: GuardrailsConfig,
    broker: BrokerProfile,
    rules: TaxRules,
    db: postgres::Client,
}

fn setup(root: &Path) -> Result<Setup> {
    let _ = dotenvy::from_path(root.join(".env"));
    let guard = GuardrailsConfig::load(root.join("config/guardrails.toml"))?;
    // G-17: questo motore esegue solo in paper. Hybrid/live richiedono un altro adapter (ManualTap).
    if guard.mode != Mode::Paper {
        bail!(
            "money-engine esegue solo in modalità paper (G-17): mode = {:?}",
            guard.mode
        );
    }
    let broker = BrokerProfile::load(root.join("config/brokers/trade_republic.toml"))?;
    let rules = TaxRules::load(root.join("config/fisco.toml"))?;
    let url = std::env::var("DATABASE_URL").context("DATABASE_URL mancante (.env)")?;
    Ok(Setup {
        guard,
        broker,
        rules,
        db: store::connect(&url)?,
    })
}

fn main() {
    if let Err(e) = run() {
        eprintln!("errore: {e:#}");
        std::process::exit(1);
    }
}

fn run() -> Result<()> {
    let cli = Cli::parse();
    let now = cli.now.unwrap_or_else(Utc::now);
    let root = repo_root()?;
    let mut s = setup(&root)?;
    let component = match cli.cmd {
        Cmd::Settle => "engine:settle",
        Cmd::Execute => "engine:execute",
        Cmd::Status => return status(&mut s),
    };
    let result = match cli.cmd {
        Cmd::Settle => settle(&mut s, now),
        Cmd::Execute => execute(&mut s, now),
        Cmd::Status => unreachable!(),
    };
    match &result {
        Ok(summary) => {
            println!("{summary}");
            store::heartbeat(&mut s.db, component, "ok", summary)?;
        }
        Err(e) => {
            let _ = store::heartbeat(&mut s.db, component, "failed", &format!("{e:#}"));
        }
    }
    result.map(|_| ())
}

fn settle(s: &mut Setup, now: DateTime<Utc>) -> Result<String> {
    let instruments = store::instruments(&mut s.db)?;
    let feed = store::feed(&mut s.db)?;
    let rates = store::rates(&mut s.db)?;
    let ctx = Ctx {
        broker: &s.broker,
        rules: &s.rules,
        guard: &s.guard,
        instruments: &instruments,
        feed: &feed,
        rates: &rates,
        now,
    };
    let mut lines = Vec::new();
    for acct in store::accounts(&mut s.db)? {
        let mut ledger = store::ledger(&mut s.db, &acct.id)?;
        let before = ledger.records().len();
        let pending = store::pending_orders(&mut s.db, &acct.id)?;
        let hist = store::equity_history(&mut s.db, &acct.id)?;
        let outcomes = plan::settle(&mut ledger, &ctx, &acct, &pending, &hist)?;
        let mut tx = s.db.transaction()?;
        let n = store::append_records(&mut tx, &ledger, before)?;
        let mut filled = 0;
        for (id, o) in &outcomes {
            match o {
                Settlement::Filled(fill) => {
                    store::mark_order(&mut tx, id, "filled", Some(fill.clone()))?;
                    filled += 1;
                }
                Settlement::Expired(reason) => store::mark_order(
                    &mut tx,
                    id,
                    "expired",
                    Some(serde_json::json!({ "reason": reason })),
                )?,
                Settlement::Waiting => {}
            }
        }
        tx.commit()?;
        lines.push(format!(
            "{}: {filled} eseguiti, {n} eventi nel ledger",
            acct.id
        ));
    }
    lines.push(poll_shadows(s)?);
    Ok(lines.join("\n"))
}

fn execute(s: &mut Setup, now: DateTime<Utc>) -> Result<String> {
    let instruments = store::instruments(&mut s.db)?;
    let feed = store::feed(&mut s.db)?;
    let rates = store::rates(&mut s.db)?;
    let ctx = Ctx {
        broker: &s.broker,
        rules: &s.rules,
        guard: &s.guard,
        instruments: &instruments,
        feed: &feed,
        rates: &rates,
        now,
    };
    let alpaca = AlpacaPaper::from_env();
    let mut lines = Vec::new();
    for acct in store::accounts(&mut s.db)? {
        let mut ledger = store::ledger(&mut s.db, &acct.id)?;
        let before = ledger.records().len();
        let hist = store::equity_history(&mut s.db, &acct.id)?;
        let intents = store::new_intents(&mut s.db, &acct.id)?;
        let outcomes = plan::execute(&mut ledger, &ctx, &intents, hist.last())?;
        let (equity, risk_event) = plan::valuate(&mut ledger, &ctx, hist.last())?;
        let mut tx = s.db.transaction()?;
        store::append_records(&mut tx, &ledger, before)?;
        let (mut ok, mut ko) = (Vec::new(), 0);
        for (intent_id, o) in &outcomes {
            match o {
                IntentOutcome::Rejected { .. } => {
                    store::mark_intent(&mut tx, *intent_id, "rejected")?;
                    ko += 1;
                }
                IntentOutcome::Submitted { order, checked } => {
                    store::insert_order(&mut tx, &acct.id, *intent_id, order)?;
                    store::mark_intent(&mut tx, *intent_id, "submitted")?;
                    ok.push((order.clone(), checked.order().notional_eur));
                }
            }
        }
        store::save_equity(&mut tx, &acct.id, &equity)?;
        tx.commit()?;
        for (order, notional_eur) in &ok {
            shadow_submit(&mut s.db, alpaca.as_ref(), order, *notional_eur)?;
        }
        lines.push(format!(
            "{}: {} ordini accettati, {ko} rifiutati · valore {} € al {} · rischio {}{}",
            acct.id,
            ok.len(),
            equity.nav.round_dp(2),
            equity.date,
            equity.risk_state,
            risk_event
                .map(|e| format!(" (evento: {e:?})"))
                .unwrap_or_default()
        ));
    }
    Ok(lines.join("\n"))
}

/// Copia l'ordine su Alpaca Paper (solo per confronto). Un errore qui non blocca il paper trading.
fn shadow_submit(
    db: &mut postgres::Client,
    alpaca: Option<&AlpacaPaper>,
    order: &plan::PendingOrder,
    notional_eur: f64,
) -> Result<()> {
    let Some(alpaca) = alpaca else { return Ok(()) };
    let (Some(symbol), Some(fx)) = (
        store::proxy_symbol(db, &order.instrument)?,
        store::last_eurusd(db)?,
    ) else {
        return Ok(());
    };
    let usd = notional_eur * fx;
    let notional = Decimal::try_from(usd).unwrap_or_default().round_dp(2);
    let side = store::side_str(order.side);
    match alpaca.submit_notional(&symbol, side, usd, &order.order_id) {
        Ok(a) => store::insert_shadow(
            db,
            &order.order_id,
            Some(&a.id),
            &symbol,
            side,
            notional,
            &a.status,
            None,
        ),
        Err(e) => store::insert_shadow(
            db,
            &order.order_id,
            None,
            &symbol,
            side,
            notional,
            "error",
            Some(&format!("{e:#}")),
        ),
    }
}

fn poll_shadows(s: &mut Setup) -> Result<String> {
    let Some(alpaca) = AlpacaPaper::from_env() else {
        return Ok("Alpaca ombra: chiavi assenti".into());
    };
    let open = store::open_shadows(&mut s.db)?;
    let mut done = 0;
    for (order_id, alpaca_id) in open {
        match alpaca.order(&alpaca_id) {
            Ok(o) => {
                let price = o
                    .filled_avg_price
                    .as_deref()
                    .and_then(|p| p.parse::<Decimal>().ok());
                let at = o
                    .filled_at
                    .as_deref()
                    .and_then(|t| DateTime::parse_from_rfc3339(t).ok())
                    .map(|t| t.with_timezone(&Utc));
                store::update_shadow(&mut s.db, &order_id, &o.status, price, at)?;
                done += usize::from(o.status == "filled");
            }
            Err(e) => eprintln!("Alpaca ombra {order_id}: {e:#}"),
        }
    }
    Ok(format!("Alpaca ombra: {done} ordini eseguiti aggiornati"))
}

fn status(s: &mut Setup) -> Result<()> {
    for acct in store::accounts(&mut s.db)? {
        let ledger = store::ledger(&mut s.db, &acct.id)?;
        let hist = store::equity_history(&mut s.db, &acct.id)?;
        let pf = ledger.portfolio();
        println!(
            "{}: {} eventi · cassa {} € · posizioni {} · ultimo valore {}",
            acct.id,
            ledger.records().len(),
            pf.cash_eur.round_dp(2),
            pf.holdings.len(),
            hist.last()
                .map(|e| format!("{} € al {} ({})", e.nav.round_dp(2), e.date, e.risk_state))
                .unwrap_or_else(|| "—".into())
        );
    }
    Ok(())
}
