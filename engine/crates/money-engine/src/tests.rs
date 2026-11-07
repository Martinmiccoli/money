//! Test della logica di una giornata (nessun database).

use std::collections::BTreeMap;

use chrono::{DateTime, NaiveDate, TimeZone, Utc};
use chrono_tz::{America::New_York, Europe::Rome};
use money_core::{
    config::GuardrailsConfig,
    costs::BrokerProfile,
    ledger::{Event, Ledger},
    tax::{TaxCategory, TaxRules},
    types::{AssetClass, Side},
};
use rust_decimal::Decimal;
use rust_decimal_macros::dec;

use crate::plan::{
    self, AccountCfg, Bar, Ctx, EquityRow, Feed, Instrument, Intent, IntentOutcome, Settlement,
};

const GUARD: &str = include_str!("../../../../config/guardrails.toml");
const TR: &str = include_str!("../../../../config/brokers/trade_republic.toml");
const FISCO: &str = include_str!("../../../../config/fisco.toml");

fn d(y: i32, m: u32, day: u32) -> NaiveDate {
    NaiveDate::from_ymd_opt(y, m, day).unwrap()
}

fn rome(date: NaiveDate, h: u32) -> DateTime<Utc> {
    Rome.from_local_datetime(&date.and_hms_opt(h, 0, 0).unwrap())
        .unwrap()
        .with_timezone(&Utc)
}

/// Barre giornaliere (feriali) dal `start`, disponibili alle 17:00 di New York.
fn feed(start: NaiveDate, prices: &[(Decimal, Decimal)]) -> Feed {
    let mut bars = Vec::new();
    let mut day = start;
    for (open, close) in prices {
        while day.weekday_num() >= 5 {
            day = day.succ_opt().unwrap();
        }
        let avail = New_York
            .from_local_datetime(&day.and_hms_opt(17, 0, 0).unwrap())
            .unwrap()
            .with_timezone(&Utc);
        bars.push(Bar {
            date: day,
            open: *open,
            close: *close,
            available_at: avail,
        });
        day = day.succ_opt().unwrap();
    }
    Feed([("etf".to_string(), bars)].into())
}

trait Wd {
    fn weekday_num(&self) -> u32;
}
impl Wd for NaiveDate {
    fn weekday_num(&self) -> u32 {
        chrono::Datelike::weekday(self).num_days_from_monday()
    }
}

struct World {
    guard: GuardrailsConfig,
    broker: BrokerProfile,
    rules: TaxRules,
    instruments: BTreeMap<String, Instrument>,
    rates: Vec<(NaiveDate, f64)>,
}

impl World {
    fn new() -> Self {
        Self {
            guard: GuardrailsConfig::from_toml_str(GUARD).unwrap(),
            broker: BrokerProfile::from_toml_str(TR).unwrap(),
            rules: TaxRules::from_toml_str(FISCO).unwrap(),
            instruments: [(
                "etf".to_string(),
                Instrument {
                    asset_class: AssetClass::EtfUcits,
                    tax_category: TaxCategory::RC,
                },
            )]
            .into(),
            rates: vec![(d(2026, 1, 1), 2.0)],
        }
    }

    fn ctx<'a>(&'a self, feed: &'a Feed, now: DateTime<Utc>) -> Ctx<'a> {
        Ctx {
            broker: &self.broker,
            rules: &self.rules,
            guard: &self.guard,
            instruments: &self.instruments,
            feed,
            rates: &self.rates,
            now,
        }
    }
}

fn acct() -> AccountCfg {
    AccountCfg {
        id: "paper-test".into(),
        initial_deposit: dec!(1000),
        monthly_deposit: dec!(0),
        started_on: d(2026, 11, 2),
    }
}

fn buy(id: i64, notional: Decimal) -> Intent {
    Intent {
        intent_id: id,
        instrument: "etf".into(),
        side: Side::Buy,
        notional_eur: Some(notional),
        qty: None,
        order_kind: "savings_plan".into(),
        expected_edge_pct: Some(dec!(4)),
        reason: "test".into(),
    }
}

#[test]
fn giornata_completa_deposito_ordine_esecuzione() {
    let w = World::new();
    // lun 2/11 … ven 6/11: prezzi a 100, poi l'apertura di martedì 10/11 a 101
    let f = feed(d(2026, 11, 2), &[(dec!(100), dec!(100)); 6]);
    let mut led = Ledger::new("paper-test");

    // martedì 3/11 alle 9:00: versamento iniziale, poi intenzione d'acquisto
    let now = rome(d(2026, 11, 3), 9);
    let s = plan::settle(&mut led, &w.ctx(&f, now), &acct(), &[], &[]).unwrap();
    assert!(s.is_empty());
    assert_eq!(led.portfolio().cash_eur, dec!(1000));

    let out = plan::execute(&mut led, &w.ctx(&f, now), &[buy(1, dec!(500))], None).unwrap();
    let IntentOutcome::Submitted { order, checked } = &out[0].1 else {
        panic!("atteso un ordine accettato: {:?}", out[0].1)
    };
    assert_eq!(order.exec_date, d(2026, 11, 3));
    assert!((checked.order().notional_eur - 499.75).abs() < 0.01);
    assert!(matches!(
        led.records().last().unwrap().event,
        Event::OrderSubmitted { .. }
    ));

    // mercoledì: l'apertura di martedì è disponibile → fill
    let now2 = rome(d(2026, 11, 4), 9);
    let s = plan::settle(
        &mut led,
        &w.ctx(&f, now2),
        &acct(),
        std::slice::from_ref(order),
        &[],
    )
    .unwrap();
    let Settlement::Filled(fill) = &s[0].1 else {
        panic!("{s:?}")
    };
    assert_eq!(fill["price_eur"], "100.0500");
    let h = &led.portfolio().holdings["etf"];
    assert_eq!(h.qty, dec!(4.997501));
    money_core::ledger::verify_chain(led.records()).unwrap();
}

#[test]
fn lunedi_mattina_dati_vecchi_g10() {
    let w = World::new();
    let f = feed(d(2026, 11, 2), &[(dec!(100), dec!(100)); 5]); // lun-ven
    let mut led = Ledger::new("paper-test");
    let monday = rome(d(2026, 11, 9), 9);
    plan::settle(&mut led, &w.ctx(&f, monday), &acct(), &[], &[]).unwrap();
    let out = plan::execute(&mut led, &w.ctx(&f, monday), &[buy(1, dec!(500))], None).unwrap();
    let IntentOutcome::Rejected { codes, .. } = &out[0].1 else {
        panic!()
    };
    assert_eq!(codes, &vec!["G-10".to_string()]);
    assert!(matches!(
        led.records().last().unwrap().event,
        Event::OrderRejected { .. }
    ));
}

#[test]
fn ordine_scade_senza_quotazioni() {
    let w = World::new();
    let f = feed(d(2026, 11, 2), &[(dec!(100), dec!(100)); 2]);
    let mut led = Ledger::new("paper-test");
    let now = rome(d(2026, 11, 3), 9);
    plan::settle(&mut led, &w.ctx(&f, now), &acct(), &[], &[]).unwrap();
    let order = plan::PendingOrder {
        order_id: "o1".into(),
        instrument: "etf".into(),
        side: Side::Buy,
        notional_eur: Some(dec!(100)),
        qty: None,
        order_kind: "regular".into(),
        exec_date: d(2026, 11, 5),
    };
    let s = plan::settle(
        &mut led,
        &w.ctx(&f, rome(d(2026, 11, 6), 9)),
        &acct(),
        std::slice::from_ref(&order),
        &[],
    )
    .unwrap();
    assert_eq!(s[0].1, Settlement::Waiting);
    let s = plan::settle(
        &mut led,
        &w.ctx(&f, rome(d(2026, 11, 13), 9)),
        &acct(),
        &[order],
        &[],
    )
    .unwrap();
    assert!(matches!(s[0].1, Settlement::Expired(_)));
}

#[test]
fn data_di_esecuzione() {
    // sabato → lunedì; dopo le 15 → giorno dopo
    assert_eq!(plan::exec_date(rome(d(2026, 11, 7), 9)), d(2026, 11, 9));
    assert_eq!(plan::exec_date(rome(d(2026, 11, 4), 16)), d(2026, 11, 5));
    assert_eq!(plan::exec_date(rome(d(2026, 11, 6), 16)), d(2026, 11, 9));
}

#[test]
fn crollo_del_20_percento_attiva_il_soft_stop() {
    let w = World::new();
    let mut f = feed(
        d(2026, 11, 2),
        &[(dec!(100), dec!(100)), (dec!(100), dec!(100))],
    );
    let mut led = Ledger::new("paper-test");
    let now = rome(d(2026, 11, 3), 9);
    plan::settle(&mut led, &w.ctx(&f, now), &acct(), &[], &[]).unwrap();
    let out = plan::execute(&mut led, &w.ctx(&f, now), &[buy(1, dec!(1000))], None).unwrap();
    let IntentOutcome::Submitted { order, .. } = &out[0].1 else {
        panic!()
    };
    let now2 = rome(d(2026, 11, 4), 9);
    plan::settle(
        &mut led,
        &w.ctx(&f, now2),
        &acct(),
        std::slice::from_ref(order),
        &[],
    )
    .unwrap();
    let (e1, _) = plan::valuate(&mut led, &w.ctx(&f, now2), None).unwrap();
    assert_eq!(e1.risk_state, "Active");
    // mercoledì chiude a 80
    let bars = f.0.get_mut("etf").unwrap();
    let mut b = bars[1].clone();
    b.date = d(2026, 11, 4);
    b.close = dec!(80);
    b.available_at += chrono::Duration::days(1);
    bars.push(b);
    let (e2, ev) = plan::valuate(&mut led, &w.ctx(&f, rome(d(2026, 11, 5), 9)), Some(&e1)).unwrap();
    assert_eq!(e2.risk_state, "Suspended");
    assert!(ev.is_some());
    assert!(matches!(
        led.records().last().unwrap().event,
        Event::RiskStateChanged { .. }
    ));
}

#[test]
fn interessi_del_mese_precedente_con_ritenuta() {
    let w = World::new();
    let f = feed(d(2026, 11, 2), &[(dec!(100), dec!(100)); 3]);
    let mut led = Ledger::new("paper-test");
    let mut a = acct();
    a.started_on = d(2026, 10, 1);
    plan::settle(&mut led, &w.ctx(&f, rome(d(2026, 10, 1), 9)), &a, &[], &[]).unwrap();
    let hist = vec![EquityRow {
        date: d(2026, 10, 1),
        nav: dec!(1000),
        cash: dec!(1000),
        invested: dec!(0),
        net_deposits: dec!(1000),
        hwm: 1000.0,
        risk_state: "Active".into(),
    }];
    plan::settle(
        &mut led,
        &w.ctx(&f, rome(d(2026, 11, 2), 9)),
        &a,
        &[],
        &hist,
    )
    .unwrap();
    // 1000 € × 2% × 31/365 = 1,698… → 1,69 €; ritenuta 26% = 0,44 €
    let kinds: Vec<_> = led.records().iter().map(|r| r.event.kind()).collect();
    assert_eq!(kinds, ["Deposit", "Interest", "TaxWithheld"]);
    assert_eq!(
        led.portfolio().cash_eur,
        dec!(1000) + dec!(1.69) - dec!(0.44)
    );
    // idempotente: rilanciare lo stesso giorno non accredita di nuovo
    plan::settle(
        &mut led,
        &w.ctx(&f, rome(d(2026, 11, 2), 10)),
        &a,
        &[],
        &hist,
    )
    .unwrap();
    assert_eq!(led.records().len(), 3);
}

#[test]
fn ripartenza_solo_da_sospeso() {
    let w = World::new();
    let f = feed(d(2026, 11, 2), &[(dec!(100), dec!(100))]);
    let mut led = Ledger::new("paper-test");
    let now = rome(d(2026, 11, 3), 9);
    plan::settle(&mut led, &w.ctx(&f, now), &acct(), &[], &[]).unwrap();
    let row = EquityRow {
        date: d(2026, 11, 2),
        nav: dec!(800),
        cash: dec!(800),
        invested: dec!(0),
        net_deposits: dec!(1000),
        hwm: 1000.0,
        risk_state: "Suspended".into(),
    };
    let after = plan::resume(&mut led, &w.ctx(&f, now), &row).unwrap();
    assert_eq!((after.risk_state.as_str(), after.hwm), ("Active", 800.0));
    assert!(matches!(
        led.records().last().unwrap().event,
        Event::RiskStateChanged { .. }
    ));
    // da attivo o bloccato non si riparte
    assert!(plan::resume(&mut led, &w.ctx(&f, now), &after).is_err());
    let locked = EquityRow {
        risk_state: "Locked".into(),
        ..row
    };
    assert!(plan::resume(&mut led, &w.ctx(&f, now), &locked).is_err());
}
