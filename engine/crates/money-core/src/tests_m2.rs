//! Test M2: costi, ledger, portafoglio e fisco. Gli importi attesi sono calcolati a mano
//! e commentati, così ogni caso è verificabile anche senza leggere il codice.

use std::collections::BTreeMap;

use chrono::{NaiveDate, TimeZone, Utc};
use rust_decimal::Decimal;
use rust_decimal_macros::dec;

use crate::{
    costs::{BrokerProfile, OrderKind},
    ledger::{verify_chain, Event, Ledger, LedgerError, NewEvent, Record, GENESIS_HASH},
    portfolio::ProjectionError,
    tax::{self, Basket, TaxCategory, TaxRules},
    types::{AssetClass, Side},
};

const TR: &str = include_str!("../../../../config/brokers/trade_republic.toml");
const FISCO: &str = include_str!("../../../../config/fisco.toml");

fn tr() -> BrokerProfile {
    BrokerProfile::from_toml_str(TR).expect("il profilo del repo deve essere valido")
}

fn rules() -> TaxRules {
    TaxRules::from_toml_str(FISCO).expect("le regole del repo devono essere valide")
}

fn d(y: i32, m: u32, day: u32) -> NaiveDate {
    NaiveDate::from_ymd_opt(y, m, day).unwrap()
}

/// Costruttore di ledger di prova: un evento per chiamata, date esplicite.
struct L {
    ledger: Ledger,
    n: u32,
}

impl L {
    fn new() -> Self {
        Self {
            ledger: Ledger::new("test"),
            n: 0,
        }
    }

    fn push(&mut self, date: NaiveDate, event: Event) -> Result<&Record, LedgerError> {
        self.n += 1;
        let ts = Utc.from_utc_datetime(&date.and_hms_opt(10, 0, 0).unwrap());
        self.ledger.append(NewEvent {
            event_id: format!("ev-{}", self.n),
            date,
            occurred_at: ts,
            recorded_at: ts,
            event,
        })
    }

    fn ok(mut self, date: NaiveDate, event: Event) -> Self {
        self.push(date, event).expect("evento valido");
        self
    }

    fn deposit(self, date: NaiveDate, amount: Decimal) -> Self {
        self.ok(date, Event::Deposit { amount_eur: amount })
    }

    fn fill(
        self,
        date: NaiveDate,
        instr: &str,
        side: Side,
        qty: Decimal,
        price: Decimal,
        fee: Decimal,
    ) -> Self {
        self.ok(date, fill(instr, side, qty, price, fee))
    }

    fn records(&self) -> &[Record] {
        self.ledger.records()
    }
}

fn fill(instr: &str, side: Side, qty: Decimal, price: Decimal, fee: Decimal) -> Event {
    fill_ext(instr, side, qty, price, fee, Decimal::ZERO, None, None)
}

#[allow(clippy::too_many_arguments)]
fn fill_ext(
    instr: &str,
    side: Side,
    qty: Decimal,
    price: Decimal,
    fee: Decimal,
    ftt: Decimal,
    settlement_date: Option<NaiveDate>,
    white_list_pct: Option<Decimal>,
) -> Event {
    Event::Fill {
        instrument: instr.into(),
        side,
        qty,
        price_eur: price,
        commission_eur: fee,
        transaction_tax_eur: ftt,
        ref_price_eur: None,
        venue: None,
        broker_order_id: None,
        settlement_date,
        white_list_pct,
    }
}

fn instruments() -> BTreeMap<String, TaxCategory> {
    BTreeMap::from([
        ("stock".to_string(), TaxCategory::RD),
        ("etc".to_string(), TaxCategory::RD),
        ("etf".to_string(), TaxCategory::RC),
        ("btc".to_string(), TaxCategory::Crypto),
    ])
}

fn report(l: &L, year: i32) -> tax::TaxReport {
    tax::report(l.records(), &rules(), &instruments(), year).unwrap()
}

// ───────────────────────────── costi ─────────────────────────────

#[test]
fn costi_profilo_del_repo_valido() {
    let p = tr();
    assert_eq!(p.fee_per_order_eur, dec!(1));
    assert_eq!(p.spread_bps[&AssetClass::EtfUcits], dec!(10));
}

#[test]
fn costi_acquisto_etf() {
    // 10 quote a 100 €, spread 10 bp => metà spread 0,05% => fill 100,05; spread pagato 0,50 €.
    let q = tr()
        .quote(
            AssetClass::EtfUcits,
            Side::Buy,
            OrderKind::Regular,
            dec!(10),
            dec!(100),
            false,
        )
        .unwrap();
    assert_eq!(q.fill_price_eur, dec!(100.05));
    assert_eq!(q.commission_eur, dec!(1));
    assert_eq!(q.spread_cost_eur, dec!(0.50));
    assert_eq!(q.ftt_eur, dec!(0));
    assert_eq!(q.total_cost_eur(), dec!(1.50));
}

#[test]
fn costi_vendita_peggiora_il_prezzo() {
    let q = tr()
        .quote(
            AssetClass::CryptoEtp,
            Side::Sell,
            OrderKind::Regular,
            dec!(1),
            dec!(50),
            false,
        )
        .unwrap();
    // 40 bp => metà 0,2% => 49,90.
    assert_eq!(q.fill_price_eur, dec!(49.90));
}

#[test]
fn costi_piano_di_accumulo_gratuito_e_ftt_solo_in_acquisto() {
    let p = tr();
    let q = p
        .quote(
            AssetClass::StockUs,
            Side::Buy,
            OrderKind::SavingsPlan,
            dec!(1),
            dec!(1000),
            true,
        )
        .unwrap();
    assert_eq!(q.commission_eur, dec!(0));
    // FTT 0,2% su 1001 € (fill con metà spread 0,1%) = 2,002 => 2,00.
    assert_eq!(q.ftt_eur, dec!(2.00));
    let s = p
        .quote(
            AssetClass::StockUs,
            Side::Sell,
            OrderKind::Regular,
            dec!(1),
            dec!(1000),
            true,
        )
        .unwrap();
    assert_eq!(s.ftt_eur, dec!(0));
}

#[test]
fn costi_ordine_da_50_euro_costa_piu_del_2_percento() {
    // Il caso reale dei 50 €: 1 € fisso + 0,025 € di spread = 2,05% => G-05 lo bloccherebbe.
    let c = tr()
        .est_side_cost_eur(
            AssetClass::EtfUcits,
            Side::Buy,
            OrderKind::Regular,
            dec!(50),
            false,
        )
        .unwrap();
    assert_eq!(c, dec!(1.025));
}

#[test]
fn costi_classe_mancante_rifiutata() {
    let broken = TR.replace("crypto_spot = 40", "");
    let e = BrokerProfile::from_toml_str(&broken)
        .unwrap_err()
        .to_string();
    assert!(e.contains("CryptoSpot"), "{e}");
}

#[test]
fn costi_valori_assurdi_rifiutati() {
    let broken = TR.replace("fee_per_order_eur = 1.0", "fee_per_order_eur = -1.0");
    assert!(BrokerProfile::from_toml_str(&broken).is_err());
    assert!(tr()
        .quote(
            AssetClass::EtfUcits,
            Side::Buy,
            OrderKind::Regular,
            dec!(0),
            dec!(10),
            false
        )
        .is_err());
}

// ───────────────────────────── ledger ─────────────────────────────

fn sample() -> L {
    L::new().deposit(d(2026, 1, 5), dec!(100)).fill(
        d(2026, 1, 6),
        "etf",
        Side::Buy,
        dec!(0.5),
        dec!(100),
        dec!(1),
    )
}

#[test]
fn ledger_catena_valida() {
    let l = sample();
    let r = l.records();
    assert_eq!(r[0].prev_hash, GENESIS_HASH);
    assert_eq!(r[1].prev_hash, r[0].hash);
    assert_eq!(r[1].seq, 2);
    verify_chain(r).unwrap();
}

#[test]
fn ledger_rileva_un_importo_modificato() {
    let mut r = sample().records().to_vec();
    r[0].event = Event::Deposit {
        amount_eur: dec!(1000),
    };
    let e = verify_chain(&r).unwrap_err();
    assert!(matches!(e, LedgerError::BrokenChain { seq: 1, .. }), "{e}");
}

#[test]
fn ledger_rileva_hash_ricalcolato_ma_catena_rotta() {
    // Chi modifica un evento e ricalcola il suo hash rompe comunque il collegamento col successivo.
    let mut r = sample().records().to_vec();
    r[0].event = Event::Deposit {
        amount_eur: dec!(1000),
    };
    r[0].hash = r[0].compute_hash();
    assert!(matches!(
        verify_chain(&r),
        Err(LedgerError::BrokenChain { seq: 2, .. })
    ));
}

#[test]
fn ledger_rileva_eventi_rimossi_o_riordinati() {
    let l = sample().deposit(d(2026, 1, 7), dec!(10));
    let mut r = l.records().to_vec();
    r.remove(1);
    assert!(verify_chain(&r).is_err());
    let mut r = l.records().to_vec();
    r.swap(1, 2);
    assert!(verify_chain(&r).is_err());
}

#[test]
fn ledger_json_andata_e_ritorno_conserva_l_hash() {
    // Il DB salva il record come JSON: rileggendolo, l'hash deve tornare identico.
    let l = sample();
    let json = serde_json::to_string(l.records()).unwrap();
    assert!(
        json.contains("\"amount_eur\":\"100\""),
        "i Decimal vanno serializzati come stringhe"
    );
    let back: Vec<Record> = serde_json::from_str(&json).unwrap();
    verify_chain(&back).unwrap();
    let rebuilt = Ledger::from_records("test", back).unwrap();
    assert_eq!(rebuilt.head_hash(), l.ledger.head_hash());
}

#[test]
fn ledger_rifiuta_vendita_scoperta_e_resta_invariato() {
    let mut l = sample();
    let head = l.ledger.head_hash().to_string();
    let e = l
        .push(
            d(2026, 1, 8),
            fill("etf", Side::Sell, dec!(1), dec!(100), dec!(1)),
        )
        .unwrap_err();
    assert!(
        matches!(e, LedgerError::Rejected(ProjectionError::Oversell { .. })),
        "{e}"
    );
    assert_eq!(l.ledger.head_hash(), head);
    assert_eq!(l.records().len(), 2);
}

#[test]
fn ledger_rifiuta_acquisto_senza_cassa_e_date_all_indietro() {
    let mut l = sample();
    // Cassa: 100 − 50 − 1 = 49 €.
    let e = l
        .push(
            d(2026, 1, 8),
            fill("etf", Side::Buy, dec!(1), dec!(49), dec!(1)),
        )
        .unwrap_err();
    assert!(matches!(
        e,
        LedgerError::Rejected(ProjectionError::InsufficientCash { .. })
    ));
    let e = l
        .push(
            d(2025, 12, 31),
            Event::Deposit {
                amount_eur: dec!(1),
            },
        )
        .unwrap_err();
    assert!(matches!(e, LedgerError::Input(_)));
}

#[test]
fn ledger_rifiuta_record_di_altri_conti() {
    let r = sample().records().to_vec();
    assert!(Ledger::from_records("altro", r).is_err());
}

// ─────────────────────────── portafoglio ───────────────────────────

#[test]
fn costo_medio_ponderato_con_commissioni() {
    // Acquisti: 1 @ 100 + 1 € e 1 @ 120 + 1 € => costo 222, medio 111.
    // Vendita: 1 @ 130 − 1 € = 129; plusvalenza 129 − 111 = 18.
    let mut l = L::new()
        .deposit(d(2026, 1, 2), dec!(500))
        .fill(
            d(2026, 1, 3),
            "stock",
            Side::Buy,
            dec!(1),
            dec!(100),
            dec!(1),
        )
        .fill(
            d(2026, 2, 3),
            "stock",
            Side::Buy,
            dec!(1),
            dec!(120),
            dec!(1),
        );
    let h = &l.ledger.portfolio().holdings["stock"];
    assert_eq!(h.cost_eur, dec!(222));
    assert_eq!(h.avg_cost_eur(), dec!(111));
    l = l.fill(
        d(2026, 3, 3),
        "stock",
        Side::Sell,
        dec!(1),
        dec!(130),
        dec!(1),
    );
    let p = l.ledger.portfolio();
    assert_eq!(p.holdings["stock"].cost_eur, dec!(111));
    // Cassa: 500 − 101 − 121 + 129 = 407.
    assert_eq!(p.cash_eur, dec!(407));
    let op = &report(&l, 2026).operations[0];
    assert_eq!(op.income_eur, dec!(18));
}

#[test]
fn vendita_totale_azzera_la_posizione() {
    let l = L::new()
        .deposit(d(2026, 1, 2), dec!(100))
        .fill(
            d(2026, 1, 3),
            "etf",
            Side::Buy,
            dec!(0.333333),
            dec!(30),
            dec!(1),
        )
        .fill(
            d(2026, 1, 4),
            "etf",
            Side::Sell,
            dec!(0.333333),
            dec!(30),
            dec!(1),
        );
    assert!(l.ledger.portfolio().holdings.is_empty());
}

#[test]
fn la_ftt_riduce_la_cassa_ma_non_entra_nel_costo_fiscale() {
    let l = L::new().deposit(d(2026, 1, 2), dec!(1000)).ok(
        d(2026, 1, 3),
        fill_ext(
            "stock",
            Side::Buy,
            dec!(1),
            dec!(500),
            dec!(1),
            dec!(1),
            None,
            None,
        ),
    );
    let p = l.ledger.portfolio();
    assert_eq!(p.cash_eur, dec!(498));
    assert_eq!(p.holdings["stock"].cost_eur, dec!(501));
}

// ───────────────────────────── fisco ─────────────────────────────

/// Compra a `buy` e vende a `sell` una quota senza commissioni: plusvalenza = sell − buy.
fn round_trip(l: L, date: NaiveDate, instr: &str, buy: Decimal, sell: Decimal) -> L {
    l.fill(date, instr, Side::Buy, dec!(1), buy, dec!(0)).fill(
        date,
        instr,
        Side::Sell,
        dec!(1),
        sell,
        dec!(0),
    )
}

fn funded() -> L {
    L::new().deposit(d(2026, 1, 2), dec!(10000))
}

#[test]
fn fisco_plusvalenza_rd_compensata_dallo_zainetto() {
    // Minusvalenza azione −30, poi plusvalenza ETC +100: imponibile 70, imposta 18,20.
    let l = round_trip(funded(), d(2026, 2, 1), "stock", dec!(100), dec!(70));
    let l = round_trip(l, d(2026, 3, 1), "etc", dec!(100), dec!(200));
    let r = report(&l, 2026);
    let rd = &r.sales[&TaxCategory::RD];
    assert_eq!(rd.gains_eur, dec!(100));
    assert_eq!(rd.losses_eur, dec!(30));
    assert_eq!(rd.losses_used_eur, dec!(30));
    assert_eq!(rd.taxable_eur, dec!(70));
    assert_eq!(rd.tax_eur, dec!(18.20));
    assert!(r.zainetto.is_empty());
}

#[test]
fn fisco_plusvalenza_etf_non_compensabile() {
    // Minusvalenza −30 nello zainetto, plusvalenza ETF +100: si paga il 26% pieno (26 €).
    let l = round_trip(funded(), d(2026, 2, 1), "stock", dec!(100), dec!(70));
    let l = round_trip(l, d(2026, 3, 1), "etf", dec!(100), dec!(200));
    let r = report(&l, 2026);
    assert_eq!(r.sales[&TaxCategory::RC].tax_eur, dec!(26.00));
    assert_eq!(r.sales[&TaxCategory::RC].losses_used_eur, dec!(0));
    assert_eq!(r.zainetto.len(), 1);
    assert_eq!(r.zainetto[0].residual_eur, dec!(30));
}

#[test]
fn fisco_minusvalenza_etf_va_nello_zainetto_e_compensa_rd() {
    // Asimmetria degli ETF: la perdita (−40) è reddito diverso e compensa una plusvalenza su azioni.
    let l = round_trip(funded(), d(2026, 2, 1), "etf", dec!(100), dec!(60));
    let l = round_trip(l, d(2026, 3, 1), "stock", dec!(100), dec!(150));
    let r = report(&l, 2026);
    assert_eq!(r.sales[&TaxCategory::RC].losses_eur, dec!(40));
    // 50 − 40 = 10 imponibile => 2,60.
    assert_eq!(r.sales[&TaxCategory::RD].tax_eur, dec!(2.60));
}

#[test]
fn fisco_la_minusvalenza_non_compensa_plusvalenze_precedenti() {
    // Plusvalenza a febbraio (+100, imposta 26), minusvalenza a marzo (−100): niente rimborso,
    // la perdita resta nello zainetto per il futuro (art. 6 c. 5 D.Lgs. 461/97, "successive").
    let l = round_trip(funded(), d(2026, 2, 1), "stock", dec!(100), dec!(200));
    let l = round_trip(l, d(2026, 3, 1), "stock", dec!(200), dec!(100));
    let r = report(&l, 2026);
    assert_eq!(r.tax_estimated_eur, dec!(26.00));
    assert_eq!(r.zainetto[0].residual_eur, dec!(100));
}

#[test]
fn fisco_zainetto_scade_il_31_12_del_quarto_anno() {
    // Perdita 2026 => utilizzabile fino al 31/12/2030.
    assert_eq!(rules().loss_expiry(2026), d(2030, 12, 31));
    let base = round_trip(funded(), d(2026, 2, 1), "stock", dec!(100), dec!(50));

    let ok = round_trip(
        base.clone_l(),
        d(2030, 12, 27), // venerdì: regolamento martedì 31/12/2030, ancora in tempo
        "stock",
        dec!(100),
        dec!(150),
    );
    assert_eq!(report(&ok, 2030).tax_estimated_eur, dec!(0));

    let late = round_trip(base, d(2031, 1, 2), "stock", dec!(100), dec!(150));
    let r = report(&late, 2031);
    assert_eq!(r.tax_estimated_eur, dec!(13.00));
    assert_eq!(r.zainetto_expired_eur, dec!(50));
    assert!(r.warnings.iter().any(|w| w.contains("scadute")));
}

#[test]
fn fisco_zainetto_consumato_dalle_perdite_piu_vecchie() {
    let l = round_trip(funded(), d(2026, 2, 1), "stock", dec!(100), dec!(80)); // −20 (2026)
    let l = round_trip(l, d(2027, 2, 1), "stock", dec!(100), dec!(70)); // −30 (2027)
    let l = round_trip(l, d(2027, 3, 1), "etc", dec!(100), dec!(125)); // +25
    let r = report(&l, 2027);
    let op = r.operations.last().unwrap();
    assert_eq!(op.losses_used.len(), 2);
    assert_eq!(
        (op.losses_used[0].origin_year, op.losses_used[0].amount_eur),
        (2026, dec!(20))
    );
    assert_eq!(
        (op.losses_used[1].origin_year, op.losses_used[1].amount_eur),
        (2027, dec!(5))
    );
    assert_eq!(r.zainetto[0].residual_eur, dec!(25));
}

#[test]
fn fisco_avviso_minusvalenze_in_scadenza() {
    let l = round_trip(funded(), d(2026, 2, 1), "stock", dec!(100), dec!(50));
    let r = report(&l, 2030);
    assert_eq!(r.zainetto_expiring_eur, dec!(50));
    assert!(r.warnings.iter().any(|w| w.contains("scadono")));
}

#[test]
fn fisco_crypto_paniere_separato_e_aliquota_33() {
    // La perdita su azioni (−50) non compensa la crypto; crypto +100 al 33% nel 2026.
    let l = round_trip(funded(), d(2026, 2, 1), "stock", dec!(100), dec!(50));
    let l = round_trip(l, d(2026, 3, 1), "btc", dec!(100), dec!(200));
    let r = report(&l, 2026);
    assert_eq!(r.sales[&TaxCategory::Crypto].tax_eur, dec!(33.00));
    assert_eq!(r.zainetto[0].basket, Basket::Ordinary);
}

#[test]
fn fisco_crypto_2025_al_26() {
    let l = L::new().deposit(d(2025, 1, 2), dec!(1000));
    let l = round_trip(l, d(2025, 6, 1), "btc", dec!(100), dec!(200));
    assert_eq!(report(&l, 2025).tax_estimated_eur, dec!(26.00));
}

#[test]
fn fisco_dividendo_usa_con_w8ben() {
    // Lordo 100, ritenuta USA 15 => netto frontiera 85, imposta italiana 26% = 22,10.
    let l = funded()
        .fill(
            d(2026, 1, 3),
            "stock",
            Side::Buy,
            dec!(1),
            dec!(100),
            dec!(0),
        )
        .ok(
            d(2026, 4, 1),
            Event::Dividend {
                instrument: "stock".into(),
                gross_eur: dec!(100),
                foreign_withholding_eur: dec!(15),
            },
        );
    let r = report(&l, 2026);
    assert_eq!(r.dividends.gross_eur, dec!(100));
    assert_eq!(r.dividends.taxable_eur, dec!(85));
    assert_eq!(r.dividends.tax_eur, dec!(22.10));
}

#[test]
fn fisco_confronto_con_trattenute_del_broker() {
    let l = round_trip(funded(), d(2026, 2, 1), "stock", dec!(100), dec!(200)).ok(
        d(2026, 2, 3),
        Event::TaxWithheld {
            amount_eur: dec!(25),
            reference: None,
        },
    );
    let r = report(&l, 2026);
    assert_eq!(r.tax_withheld_by_broker_eur, dec!(25));
    assert_eq!(r.difference_eur, dec!(1.00));
    assert!(r.warnings.iter().any(|w| w.contains("differenza")));
    assert!(r.disclaimer.contains("commercialista"));
}

#[test]
fn fisco_strumento_senza_categoria_e_errore() {
    let l = round_trip(funded(), d(2026, 2, 1), "ignoto", dec!(100), dec!(200));
    assert!(tax::report(l.records(), &rules(), &instruments(), 2026).is_err());
}

#[test]
fn fisco_imposta_dovuta_sull_ultima_operazione() {
    let l = round_trip(funded(), d(2026, 2, 1), "stock", dec!(100), dec!(150));
    assert_eq!(
        tax::tax_due_for_last(l.records(), &rules(), &instruments()).unwrap(),
        dec!(13.00)
    );
}

#[test]
fn fisco_bollo_su_50_euro_per_un_anno() {
    // 50 € × 0,2% = 0,10 € l'anno.
    let days: Vec<_> = d(2026, 1, 1)
        .iter_days()
        .take(365)
        .map(|day| (day, dec!(50)))
        .collect();
    assert_eq!(tax::stamp_duty_estimate(&rules(), &days), dec!(0.10));
}

#[test]
fn fisco_regole_senza_fonte_rifiutate() {
    // Svuota la fonte della prima aliquota, qualunque sia il testo.
    let start = FISCO.find("source = \"").unwrap() + "source = \"".len();
    let end = start + FISCO[start..].find('"').unwrap();
    let broken = format!("{}{}", &FISCO[..start], &FISCO[end..]);
    assert!(TaxRules::from_toml_str(&broken).is_err());
}

impl L {
    fn clone_l(&self) -> L {
        L {
            ledger: self.ledger.clone(),
            n: self.n,
        }
    }
}

#[test]
fn fisco_data_di_regolamento_stimata() {
    // Gio 24/12/2026: 25 e 26 festivi, weekend => lun 28 (1), mar 29 (2).
    assert_eq!(tax::settlement_estimate(d(2026, 12, 24)), d(2026, 12, 29));
    // Lun 30/12/2030: mar 31 (1), 1/1 festivo, gio 2/1/2031 (2).
    assert_eq!(tax::settlement_estimate(d(2030, 12, 30)), d(2031, 1, 2));
    assert_eq!(tax::settlement_estimate(d(2026, 11, 6)), d(2026, 11, 10));
}

#[test]
fn fisco_vendita_a_cavallo_d_anno_va_nell_anno_successivo() {
    // Il caso dell'ABF Milano 8876/2025: vendita il 30/12 regolata il 2/1 => la perdita 2026
    // in scadenza il 31/12/2030 non può più compensarla.
    let l = round_trip(funded(), d(2026, 2, 1), "stock", dec!(100), dec!(50));
    let l = round_trip(l, d(2030, 12, 30), "stock", dec!(100), dec!(150));
    assert_eq!(report(&l, 2030).tax_estimated_eur, dec!(0));
    let r = report(&l, 2031);
    assert_eq!(r.tax_estimated_eur, dec!(13.00));
    let op = &r.operations[0];
    assert_eq!((op.trade_date, op.date), (d(2030, 12, 30), d(2031, 1, 2)));
    assert!(
        r.warnings.iter().any(|w| w.contains("regolata")),
        "{:?}",
        r.warnings
    );
}

#[test]
fn fisco_data_di_regolamento_esplicita_prevale() {
    let l = funded()
        .fill(
            d(2026, 3, 2),
            "stock",
            Side::Buy,
            dec!(1),
            dec!(100),
            dec!(0),
        )
        .ok(
            d(2026, 12, 30),
            fill_ext(
                "stock",
                Side::Sell,
                dec!(1),
                dec!(150),
                dec!(0),
                dec!(0),
                Some(d(2026, 12, 31)),
                None,
            ),
        );
    assert_eq!(report(&l, 2026).tax_estimated_eur, dec!(13.00));
}

#[test]
fn fisco_etf_white_list_riduce_guadagni_e_perdite() {
    // ETF con il 50% in titoli di Stato white list: rilevante = 50% + 50% × 48,08% = 74,04%.
    let sell_wl = |price| {
        fill_ext(
            "etf",
            Side::Sell,
            dec!(1),
            price,
            dec!(0),
            dec!(0),
            None,
            Some(dec!(50)),
        )
    };
    let gain = funded()
        .fill(d(2026, 3, 2), "etf", Side::Buy, dec!(1), dec!(100), dec!(0))
        .ok(d(2026, 3, 2), sell_wl(dec!(200)));
    let op = &report(&gain, 2026).operations[0];
    assert_eq!(op.income_eur, dec!(100));
    assert_eq!(op.taxable_eur, dec!(74.04));
    assert_eq!(op.tax_eur, dec!(19.25)); // 74,04 × 26% = 19,2504

    let loss = funded()
        .fill(d(2026, 3, 2), "etf", Side::Buy, dec!(1), dec!(200), dec!(0))
        .ok(d(2026, 3, 2), sell_wl(dec!(100)));
    let r = report(&loss, 2026);
    assert_eq!(r.operations[0].loss_added_eur, dec!(74.04));
    assert_eq!(r.zainetto[0].residual_eur, dec!(74.04));
}

#[test]
fn ledger_valida_regolamento_e_white_list() {
    let mut l = sample();
    let sell = |sd, wl| {
        fill_ext(
            "etf",
            Side::Sell,
            dec!(0.1),
            dec!(100),
            dec!(0),
            dec!(0),
            sd,
            wl,
        )
    };
    let bad_date = sell(Some(d(2026, 1, 1)), None);
    assert!(matches!(
        l.push(d(2026, 1, 8), bad_date),
        Err(LedgerError::Input(_))
    ));
    let bad_pct = sell(None, Some(dec!(150)));
    assert!(matches!(
        l.push(d(2026, 1, 8), bad_pct),
        Err(LedgerError::Input(_))
    ));
}

#[test]
fn fisco_interessi_sulla_liquidita_al_26() {
    // 10 € di interessi lordi => 2,60 € di imposta, senza compensazione con lo zainetto.
    let l = round_trip(funded(), d(2026, 2, 1), "stock", dec!(100), dec!(50)).ok(
        d(2026, 3, 1),
        Event::Interest {
            amount_eur: dec!(10),
        },
    );
    let r = report(&l, 2026);
    assert_eq!(r.interest.tax_eur, dec!(2.60));
    assert_eq!(r.tax_estimated_eur, dec!(2.60));
    assert_eq!(r.zainetto[0].residual_eur, dec!(50));
    assert_eq!(
        l.ledger.portfolio().cash_eur,
        dec!(10000) - dec!(50) + dec!(10)
    );
}

#[test]
fn checked_order_solo_dai_guardrails() {
    use crate::{
        config::GuardrailsConfig,
        guardrails::check,
        risk::RiskState,
        types::{OrderRequest, PortfolioSnapshot},
    };
    let cfg = GuardrailsConfig::from_toml_str(include_str!("../../../../config/guardrails.toml"))
        .unwrap();
    let pf = PortfolioSnapshot {
        equity_eur: 100.0,
        cash_eur: 100.0,
        data_age_hours: 1.0,
        ..Default::default()
    };
    let o = OrderRequest {
        instrument: "x".into(),
        asset_class: AssetClass::EtfUcits,
        side: Side::Buy,
        notional_eur: 50.0,
        est_cost_eur: 0.03,
        expected_edge_pct: Some(1.0),
        ref_price: 10.0,
        limit_price: None,
        valid_for_hours: None,
    };
    let ok = check(&cfg, RiskState::Active, &pf, o.clone()).unwrap();
    assert_eq!(ok.order().notional_eur, 50.0);
    assert!(check(&cfg, RiskState::Locked, &pf, o).is_err());
}

#[test]
fn eventi_degli_ordini_non_toccano_il_portafoglio() {
    let l = sample().ok(
        d(2026, 1, 9),
        Event::OrderRejected {
            instrument: "etf".into(),
            side: Side::Buy,
            codes: vec!["G-10".into()],
            detail: "dati vecchi".into(),
        },
    );
    assert_eq!(l.ledger.portfolio().cash_eur, dec!(49));
    verify_chain(l.records()).unwrap();
}
