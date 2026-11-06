use crate::{
    config::GuardrailsConfig,
    guardrails::{check_order, Violation},
    risk::{ResumeError, RiskEvent, RiskMachine, RiskState},
    types::{AssetClass, Mode, OrderRequest, PortfolioSnapshot, Position, Side},
};

const REPO_CONFIG: &str = include_str!("../../../../config/guardrails.toml");
const HASH: &str = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";

fn cfg() -> GuardrailsConfig {
    GuardrailsConfig::from_toml_str(REPO_CONFIG).expect("la config del repo deve essere valida")
}

fn cfg_with(mode: Mode) -> GuardrailsConfig {
    let mut c = cfg();
    c.mode = mode;
    c.validation_report_sha256 = HASH.into();
    c.validate().unwrap();
    c
}

fn pf(equity: f64, cash: f64) -> PortfolioSnapshot {
    PortfolioSnapshot {
        equity_eur: equity,
        cash_eur: cash,
        data_age_hours: 1.0,
        ..Default::default()
    }
}

fn buy(class: AssetClass, notional: f64, cost: f64, edge: f64) -> OrderRequest {
    OrderRequest {
        instrument: "TEST".into(),
        asset_class: class,
        side: Side::Buy,
        notional_eur: notional,
        est_cost_eur: cost,
        expected_edge_pct: Some(edge),
        ref_price: 100.0,
        limit_price: Some(100.5),
        valid_for_hours: Some(48),
    }
}

fn codes(r: Result<(), Vec<Violation>>) -> Vec<&'static str> {
    r.err()
        .unwrap_or_default()
        .iter()
        .map(|v| v.code())
        .collect()
}

// ---------- configurazione ----------

#[test]
fn repo_config_is_valid_and_paper() {
    assert_eq!(cfg().mode, Mode::Paper);
}

#[test]
fn real_money_requires_validation_hash() {
    let toml = REPO_CONFIG.replace("mode = \"paper\"", "mode = \"live\"");
    let err = GuardrailsConfig::from_toml_str(&toml)
        .unwrap_err()
        .to_string();
    assert!(err.contains("G-15"), "{err}");
}

#[test]
fn hard_ceilings_cannot_be_exceeded() {
    let toml = REPO_CONFIG
        .replace("soft_stop_pct = 15.0", "soft_stop_pct = 40.0")
        .replace("max_cost_ratio_pct = 2.0", "max_cost_ratio_pct = 9.0");
    let err = GuardrailsConfig::from_toml_str(&toml)
        .unwrap_err()
        .to_string();
    assert!(
        err.contains("soft_stop_pct") && err.contains("max_cost_ratio_pct"),
        "{err}"
    );
}

#[test]
fn crypto_spot_never_with_real_money() {
    let toml = REPO_CONFIG.replace(
        "real_money = [\"stock_us\", \"etf_ucits\", \"crypto_etp\"]",
        "real_money = [\"stock_us\", \"etf_ucits\", \"crypto_etp\", \"crypto_spot\"]",
    );
    assert!(GuardrailsConfig::from_toml_str(&toml).is_err());
}

#[test]
fn unknown_fields_rejected() {
    let toml = format!("{REPO_CONFIG}\n[extra]\nfoo = 1\n");
    assert!(GuardrailsConfig::from_toml_str(&toml).is_err());
}

// ---------- G-13 strumenti ----------

#[test]
fn crypto_spot_only_in_paper() {
    let o = buy(AssetClass::CryptoSpot, 5.0, 0.0, 1.0);
    assert!(check_order(&cfg(), RiskState::Active, &pf(100.0, 100.0), &o).is_ok());
    let r = check_order(
        &cfg_with(Mode::Live),
        RiskState::Active,
        &pf(100.0, 100.0),
        &o,
    );
    assert!(codes(r).contains(&"G-13"));
}

// ---------- G-01 / G-02 ----------

#[test]
fn suspended_blocks_buys_but_allows_sells() {
    let c = cfg();
    let mut p = pf(100.0, 50.0);
    p.positions.insert(
        "TEST".into(),
        Position {
            asset_class: AssetClass::EtfUcits,
            value_eur: 50.0,
        },
    );
    let b = buy(AssetClass::EtfUcits, 10.0, 0.0, 1.0);
    assert!(codes(check_order(&c, RiskState::Suspended, &p, &b)).contains(&"G-01"));
    let s = OrderRequest {
        side: Side::Sell,
        ..b
    };
    assert!(check_order(&c, RiskState::Suspended, &p, &s).is_ok());
}

#[test]
fn locked_blocks_everything() {
    let c = cfg();
    let mut p = pf(100.0, 50.0);
    p.positions.insert(
        "TEST".into(),
        Position {
            asset_class: AssetClass::EtfUcits,
            value_eur: 50.0,
        },
    );
    let s = OrderRequest {
        side: Side::Sell,
        ..buy(AssetClass::EtfUcits, 10.0, 0.0, 1.0)
    };
    assert!(codes(check_order(&c, RiskState::Locked, &p, &s)).contains(&"G-02"));
}

// ---------- G-03 / G-04 ----------

#[test]
fn no_short_selling() {
    let s = OrderRequest {
        side: Side::Sell,
        ..buy(AssetClass::StockUs, 10.0, 0.0, 1.0)
    };
    assert!(codes(check_order(
        &cfg(),
        RiskState::Active,
        &pf(100.0, 100.0),
        &s
    ))
    .contains(&"G-03"));
}

#[test]
fn no_negative_cash() {
    let o = buy(AssetClass::EtfUcits, 50.0, 0.0, 1.0);
    assert!(codes(check_order(
        &cfg(),
        RiskState::Active,
        &pf(100.0, 49.99),
        &o
    ))
    .contains(&"G-04"));
}

// ---------- G-05 / G-06: i costi con 50 € ----------

#[test]
fn one_euro_fee_on_ten_euro_order_is_rejected() {
    // 1 € su 10 € = 10% di costo: è proprio il caso reale con 50 € su Trade Republic.
    let o = buy(AssetClass::EtfUcits, 10.0, 1.0, 50.0);
    assert!(codes(check_order(&cfg(), RiskState::Active, &pf(50.0, 50.0), &o)).contains(&"G-05"));
}

#[test]
fn savings_plan_with_zero_fee_is_allowed() {
    let o = buy(AssetClass::EtfUcits, 10.0, 0.0, 0.5);
    assert!(check_order(&cfg(), RiskState::Active, &pf(50.0, 50.0), &o).is_ok());
}

#[test]
fn edge_must_cover_round_trip_costs() {
    // costo 1% -> round trip 2% -> serve edge >= 2 * 2% = 4%
    let c = cfg();
    let p = pf(1000.0, 1000.0);
    let low = buy(AssetClass::EtfUcits, 100.0, 1.0, 3.9);
    assert!(codes(check_order(&c, RiskState::Active, &p, &low)).contains(&"G-06"));
    let ok = buy(AssetClass::EtfUcits, 100.0, 1.0, 4.0);
    assert!(check_order(&c, RiskState::Active, &p, &ok).is_ok());
    let none = OrderRequest {
        expected_edge_pct: None,
        ..ok
    };
    assert!(codes(check_order(&c, RiskState::Active, &p, &none)).contains(&"G-06"));
}

// ---------- G-07 / G-08 / G-10 ----------

#[test]
fn order_frequency_limits() {
    let mut p = pf(100.0, 100.0);
    p.orders_today = 3;
    let o = buy(AssetClass::EtfUcits, 10.0, 0.0, 1.0);
    assert!(codes(check_order(&cfg(), RiskState::Active, &p, &o)).contains(&"G-07"));
}

#[test]
fn single_stock_concentration() {
    let o = buy(AssetClass::StockUs, 21.0, 0.0, 1.0);
    assert!(codes(check_order(
        &cfg(),
        RiskState::Active,
        &pf(100.0, 100.0),
        &o
    ))
    .contains(&"G-08"));
    let o = buy(AssetClass::StockUs, 20.0, 0.0, 1.0);
    assert!(check_order(&cfg(), RiskState::Active, &pf(100.0, 100.0), &o).is_ok());
}

#[test]
fn crypto_total_cap_counts_existing_positions() {
    let mut p = pf(100.0, 100.0);
    p.positions.insert(
        "BTC-ETP".into(),
        Position {
            asset_class: AssetClass::CryptoEtp,
            value_eur: 10.0,
        },
    );
    let o = OrderRequest {
        instrument: "ETH-ETP".into(),
        ..buy(AssetClass::CryptoEtp, 6.0, 0.0, 1.0)
    };
    assert!(codes(check_order(&cfg(), RiskState::Active, &p, &o)).contains(&"G-08"));
}

#[test]
fn stale_data_blocks_trading() {
    let mut p = pf(100.0, 100.0);
    p.data_age_hours = 48.0;
    let o = buy(AssetClass::EtfUcits, 10.0, 0.0, 1.0);
    assert!(codes(check_order(&cfg(), RiskState::Active, &p, &o)).contains(&"G-10"));
    p.data_age_hours = f64::NAN;
    assert!(codes(check_order(&cfg(), RiskState::Active, &p, &o)).contains(&"G-10"));
}

// ---------- G-09 hybrid ----------

#[test]
fn hybrid_requires_limit_and_expiry() {
    let c = cfg_with(Mode::Hybrid);
    let p = pf(100.0, 100.0);
    let o = OrderRequest {
        limit_price: None,
        valid_for_hours: None,
        ..buy(AssetClass::EtfUcits, 10.0, 0.0, 1.0)
    };
    let cs = codes(check_order(&c, RiskState::Active, &p, &o));
    assert_eq!(cs.iter().filter(|c| **c == "G-09").count(), 2);

    let far = OrderRequest {
        limit_price: Some(103.0),
        ..buy(AssetClass::EtfUcits, 10.0, 0.0, 1.0)
    };
    assert!(codes(check_order(&c, RiskState::Active, &p, &far)).contains(&"G-09"));

    let ok = buy(AssetClass::EtfUcits, 10.0, 0.0, 1.0);
    assert!(check_order(&c, RiskState::Active, &p, &ok).is_ok());
}

// ---------- input non validi ----------

#[test]
fn garbage_inputs_never_pass() {
    let p = pf(100.0, 100.0);
    for bad in [f64::NAN, f64::INFINITY, -5.0, 0.0] {
        let o = buy(AssetClass::EtfUcits, bad, 0.0, 1.0);
        assert!(
            check_order(&cfg(), RiskState::Active, &p, &o).is_err(),
            "notional {bad}"
        );
    }
}

// ---------- macchina a stati del rischio ----------

#[test]
fn soft_stop_at_15pct_from_high_water_mark() {
    let c = cfg();
    let mut r = RiskMachine::new(50.0);
    assert_eq!(r.update(&c, 60.0), None); // nuovo massimo: 60
    assert_eq!(r.update(&c, 51.5), None); // -14,2%
    assert!(matches!(
        r.update(&c, 51.0),
        Some(RiskEvent::SoftStopTriggered { .. })
    )); // -15%
    assert_eq!(r.state(), RiskState::Suspended);
    // resta sospeso anche se l'equity risale, finché l'utente non fa resume
    assert_eq!(r.update(&c, 70.0), None);
    assert_eq!(r.state(), RiskState::Suspended);
    assert!(matches!(r.resume(70.0), Ok(RiskEvent::Resumed { .. })));
    assert_eq!(r.state(), RiskState::Active);
    assert_eq!(r.high_water_mark_eur(), 70.0);
}

#[test]
fn kill_switch_at_50pct_of_deposits_is_permanent() {
    let c = cfg();
    let mut r = RiskMachine::new(50.0);
    assert!(matches!(
        r.update(&c, 25.0),
        Some(RiskEvent::KillSwitchTriggered { .. })
    ));
    assert_eq!(r.state(), RiskState::Locked);
    assert_eq!(r.update(&c, 100.0), None);
    assert_eq!(r.state(), RiskState::Locked);
    assert_eq!(r.resume(100.0), Err(ResumeError::Locked));
}

#[test]
fn kill_switch_fires_even_while_suspended_and_on_nan() {
    let c = cfg();
    let mut r = RiskMachine::new(50.0);
    r.update(&c, 42.0); // -16% -> sospeso
    assert_eq!(r.state(), RiskState::Suspended);
    r.update(&c, 24.0);
    assert_eq!(r.state(), RiskState::Locked);

    let mut r = RiskMachine::new(50.0);
    r.update(&c, f64::NAN);
    assert_eq!(r.state(), RiskState::Locked);
}

#[test]
fn resume_only_from_suspended() {
    let mut r = RiskMachine::new(50.0);
    assert_eq!(r.resume(50.0), Err(ResumeError::NotSuspended));
}
