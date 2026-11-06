//! Motore fiscale deterministico (3.4, ADR-004): regime amministrato, persona fisica residente.
//!
//! Ripercorre il ledger di un conto in ordine e, per ogni vendita e dividendo, calcola
//! l'imposta stimata. Le regole sono in `config/fisco.toml`, le fonti in `knowledge/fisco/`.
//!
//! | Categoria | Plusvalenza | Minusvalenza |
//! |---|---|---|
//! | RD (azioni, ETC/ETN, ETP crypto) | compensabile con lo zainetto, poi 26% | nello zainetto ordinario |
//! | RC (ETF/OICR) | 26% **senza** compensazione | nello zainetto ordinario (è RD) |
//! | CRYPTO (spot, solo paper) | zainetto crypto separato, poi aliquota crypto | nello zainetto crypto |
//!
//! Lo zainetto si consuma partendo dalle perdite più vecchie; le perdite dell'anno N
//! scadono il 31/12 dell'anno N + `loss_carryforward_years`. Una minusvalenza compensa
//! solo plusvalenze realizzate **dopo** di essa (art. 6 c. 5 D.Lgs. 461/1997).
//!
//! L'anno fiscale di una vendita è quello della **data di regolamento** (T+2): così dice
//! l'AdE per gli OICR (circ. 19/E/2014 §5.1) e per prudenza lo applichiamo a tutto.
//!
//! I numeri sono **stime**: vanno confrontati con le trattenute del broker (`TaxWithheld`)
//! e verificati da un commercialista prima di qualsiasi dichiarazione.

use std::{collections::BTreeMap, path::Path};

use chrono::{Datelike, Days, NaiveDate, Weekday};
use rust_decimal::{Decimal, RoundingStrategy};
use rust_decimal_macros::dec;
use serde::{Deserialize, Serialize};
use thiserror::Error;

use crate::{
    costs::round_cents,
    ledger::{Event, Record},
    portfolio::{Portfolio, ProjectionError},
};

pub const DISCLAIMER: &str =
    "Stima deterministica del motore fiscale: non sostituisce un commercialista. \
Ogni dato va verificato da un professionista prima di qualsiasi dichiarazione.";

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
pub enum TaxCategory {
    /// Redditi diversi: plusvalenze compensabili.
    RD,
    /// Redditi di capitale (plusvalenze da ETF/OICR): non compensabili.
    RC,
    /// Cripto-attività spot: paniere separato.
    #[serde(rename = "CRYPTO")]
    Crypto,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Basket {
    Ordinary,
    Crypto,
}

impl TaxCategory {
    pub fn basket(self) -> Basket {
        match self {
            TaxCategory::RD | TaxCategory::RC => Basket::Ordinary,
            TaxCategory::Crypto => Basket::Crypto,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct RateRule {
    pub basket: Basket,
    pub from: NaiveDate,
    pub pct: Decimal,
    pub source: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct TaxRules {
    pub verified_on: NaiveDate,
    pub loss_carryforward_years: i32,
    pub stamp_duty_pct_per_year: Decimal,
    /// Quota imponibile dei redditi da titoli di Stato "white list" (48,08% => 12,5% effettivo).
    pub white_list_taxable_share_pct: Decimal,
    pub rate: Vec<RateRule>,
}

#[derive(Debug, Error)]
pub enum TaxError {
    #[error("impossibile leggere le regole fiscali: {0}")]
    Io(#[from] std::io::Error),
    #[error("regole fiscali non valide (sintassi): {0}")]
    Parse(#[from] toml::de::Error),
    #[error("regole fiscali non valide: {0}")]
    Invalid(String),
    #[error("nessuna aliquota per il paniere {basket:?} alla data {date}")]
    NoRate { basket: Basket, date: NaiveDate },
    #[error(
        "categoria fiscale sconosciuta per lo strumento {0}: va dichiarata in config/universe.toml"
    )]
    UnknownInstrument(String),
    #[error("ledger incoerente al record seq={seq}: {source}")]
    Ledger { seq: u64, source: ProjectionError },
}

impl TaxRules {
    pub fn load(path: impl AsRef<Path>) -> Result<Self, TaxError> {
        Self::from_toml_str(&std::fs::read_to_string(path)?)
    }

    pub fn from_toml_str(s: &str) -> Result<Self, TaxError> {
        let r: Self = toml::from_str(s)?;
        r.validate()?;
        Ok(r)
    }

    pub fn validate(&self) -> Result<(), TaxError> {
        let mut e = Vec::new();
        if !(1..=10).contains(&self.loss_carryforward_years) {
            e.push("loss_carryforward_years deve stare in [1, 10]".to_string());
        }
        if !(Decimal::ZERO..=dec!(1)).contains(&self.stamp_duty_pct_per_year) {
            e.push("stamp_duty_pct_per_year deve stare in [0, 1]".to_string());
        }
        if !(Decimal::ZERO < self.white_list_taxable_share_pct
            && self.white_list_taxable_share_pct <= Decimal::ONE_HUNDRED)
        {
            e.push("white_list_taxable_share_pct deve stare in (0, 100]".to_string());
        }
        for b in [Basket::Ordinary, Basket::Crypto] {
            if !self.rate.iter().any(|r| r.basket == b) {
                e.push(format!("manca un'aliquota per il paniere {b:?}"));
            }
        }
        for r in &self.rate {
            if !(dec!(0) < r.pct && r.pct <= dec!(60)) {
                e.push(format!(
                    "aliquota {:?} dal {} fuori da (0, 60]",
                    r.basket, r.from
                ));
            }
            if r.source.trim().is_empty() {
                e.push(format!(
                    "aliquota {:?} dal {} senza fonte",
                    r.basket, r.from
                ));
            }
        }
        if e.is_empty() {
            Ok(())
        } else {
            Err(TaxError::Invalid(e.join("; ")))
        }
    }

    pub fn rate_pct(&self, basket: Basket, date: NaiveDate) -> Result<Decimal, TaxError> {
        self.rate
            .iter()
            .filter(|r| r.basket == basket && r.from <= date)
            .max_by_key(|r| r.from)
            .map(|r| r.pct)
            .ok_or(TaxError::NoRate { basket, date })
    }

    /// Ultimo giorno in cui una perdita dell'anno `origin_year` è utilizzabile.
    pub fn loss_expiry(&self, origin_year: i32) -> NaiveDate {
        NaiveDate::from_ymd_opt(origin_year + self.loss_carryforward_years, 12, 31)
            .expect("data valida")
    }
}

/// Stima della data di regolamento: T+2 giorni lavorativi, saltando weekend e le festività
/// fisse del calendario TARGET (1/1, 1/5, 25/12, 26/12). Pasqua non incide sul cambio d'anno.
pub fn settlement_estimate(trade_date: NaiveDate) -> NaiveDate {
    let mut d = trade_date;
    let mut left = 2;
    while left > 0 {
        d = d + Days::new(1);
        let holiday = matches!((d.month(), d.day()), (1, 1) | (5, 1) | (12, 25) | (12, 26));
        if !matches!(d.weekday(), Weekday::Sat | Weekday::Sun) && !holiday {
            left -= 1;
        }
    }
    d
}

/// Arrotondamento dell'imposta al centesimo.
fn round_tax(v: Decimal) -> Decimal {
    v.round_dp_with_strategy(2, RoundingStrategy::MidpointAwayFromZero)
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum OperationKind {
    Sale,
    Dividend,
}

/// Utilizzo dello zainetto in un'operazione.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct LossUse {
    pub origin_year: i32,
    pub amount_eur: Decimal,
}

/// Dettaglio fiscale di una singola operazione: ogni numero del report è tracciabile qui.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct TaxOperation {
    pub seq: u64,
    /// Data che fa fede per il fisco (regolamento per le vendite).
    pub date: NaiveDate,
    /// Data dell'operazione registrata nel ledger.
    pub trade_date: NaiveDate,
    pub instrument: String,
    pub category: TaxCategory,
    pub kind: OperationKind,
    /// Plusvalenza (positiva) o minusvalenza (negativa); per i dividendi, il netto frontiera.
    pub income_eur: Decimal,
    pub losses_used: Vec<LossUse>,
    pub taxable_eur: Decimal,
    pub rate_pct: Decimal,
    pub tax_eur: Decimal,
    /// Minusvalenza aggiunta allo zainetto.
    pub loss_added_eur: Decimal,
    /// % white list applicata (solo ETF con titoli di Stato).
    pub white_list_pct: Option<Decimal>,
    /// Punti da verificare su questa operazione.
    pub notes: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ZainettoEntry {
    pub basket: Basket,
    pub origin_year: i32,
    pub expires_on: NaiveDate,
    pub residual_eur: Decimal,
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct CategorySummary {
    pub gains_eur: Decimal,
    pub losses_eur: Decimal,
    pub losses_used_eur: Decimal,
    pub taxable_eur: Decimal,
    pub tax_eur: Decimal,
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct DividendSummary {
    pub gross_eur: Decimal,
    pub foreign_withholding_eur: Decimal,
    pub taxable_eur: Decimal,
    pub tax_eur: Decimal,
}

/// Report fiscale annuale, deterministico. Lo legge e lo spiega l'agente fiscale (ADR-004).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct TaxReport {
    pub account: String,
    pub year: i32,
    pub rules_verified_on: NaiveDate,
    pub sales: BTreeMap<TaxCategory, CategorySummary>,
    pub dividends: DividendSummary,
    pub tax_estimated_eur: Decimal,
    /// Somma degli eventi `TaxWithheld` dell'anno (trattenute meno restituzioni).
    pub tax_withheld_by_broker_eur: Decimal,
    /// Stimato − trattenuto: se diverso da zero va spiegato.
    pub difference_eur: Decimal,
    pub stamp_duty_charged_eur: Decimal,
    /// Zainetto residuo al 31/12 dell'anno (solo voci non scadute).
    pub zainetto: Vec<ZainettoEntry>,
    /// Perdite che scadono il 31/12 di quest'anno: usarle o perderle.
    pub zainetto_expiring_eur: Decimal,
    /// Perdite scadute non utilizzate (perse definitivamente) alla fine dell'anno precedente.
    pub zainetto_expired_eur: Decimal,
    pub operations: Vec<TaxOperation>,
    pub warnings: Vec<String>,
    pub disclaimer: String,
}

/// Stato del motore fiscale durante la scansione del ledger.
#[derive(Debug, Clone, Default)]
pub struct TaxEngine {
    portfolio: Portfolio,
    zainetto: BTreeMap<(Basket, i32), Decimal>,
    operations: Vec<TaxOperation>,
}

impl TaxEngine {
    fn add_loss(&mut self, basket: Basket, year: i32, amount: Decimal) {
        *self.zainetto.entry((basket, year)).or_default() += amount;
    }

    /// Consuma lo zainetto, dalle perdite più vecchie, per compensare `gain`.
    fn use_losses(
        &mut self,
        rules: &TaxRules,
        basket: Basket,
        date: NaiveDate,
        gain: Decimal,
    ) -> Vec<LossUse> {
        let mut remaining = gain;
        let mut used = Vec::new();
        for ((b, year), residual) in self.zainetto.iter_mut() {
            if remaining.is_zero() {
                break;
            }
            if *b != basket || residual.is_zero() || date > rules.loss_expiry(*year) {
                continue;
            }
            let take = remaining.min(*residual);
            *residual -= take;
            remaining -= take;
            used.push(LossUse {
                origin_year: *year,
                amount_eur: take,
            });
        }
        used
    }

    fn process(
        &mut self,
        r: &Record,
        rules: &TaxRules,
        instruments: &BTreeMap<String, TaxCategory>,
    ) -> Result<(), TaxError> {
        let category_of = |i: &str| {
            instruments
                .get(i)
                .copied()
                .ok_or_else(|| TaxError::UnknownInstrument(i.to_string()))
        };
        let realization = self
            .portfolio
            .apply(&r.event)
            .map_err(|source| TaxError::Ledger { seq: r.seq, source })?;

        if let Some(real) = realization {
            let (settlement, white_list_pct) = match &r.event {
                Event::Fill {
                    settlement_date,
                    white_list_pct,
                    ..
                } => (*settlement_date, *white_list_pct),
                _ => (None, None),
            };
            let mut notes = Vec::new();
            let fiscal_date = settlement.unwrap_or_else(|| settlement_estimate(r.date));
            if fiscal_date.year() != r.date.year() {
                notes.push(format!(
                    "vendita del {} regolata il {}: attribuita al {} (verificare con l'estratto del broker)",
                    r.date,
                    fiscal_date,
                    fiscal_date.year()
                ));
            } else if settlement.is_none() && r.date.month() == 12 && r.date.day() >= 20 {
                notes.push(format!(
                    "vendita di fine anno ({}) senza data di regolamento: anno fiscale stimato",
                    r.date
                ));
            }
            let category = category_of(&real.instrument)?;
            let basket = category.basket();
            let gain = round_cents(real.gain_eur);
            // Quota rilevante: la parte riferibile ai titoli di Stato white list conta solo per il
            // 48,08%, sia in guadagno sia in perdita (DM 13/12/2011 art. 1 c. 1-4).
            let factor = match white_list_pct {
                Some(p) => {
                    let p = p / Decimal::ONE_HUNDRED;
                    (Decimal::ONE - p)
                        + p * rules.white_list_taxable_share_pct / Decimal::ONE_HUNDRED
                }
                None => Decimal::ONE,
            };
            let relevant = round_cents(gain * factor);
            let rate = rules.rate_pct(basket, fiscal_date)?;
            let mut op = TaxOperation {
                seq: r.seq,
                date: fiscal_date,
                trade_date: r.date,
                instrument: real.instrument.clone(),
                category,
                kind: OperationKind::Sale,
                income_eur: gain,
                losses_used: Vec::new(),
                taxable_eur: Decimal::ZERO,
                rate_pct: rate,
                tax_eur: Decimal::ZERO,
                loss_added_eur: Decimal::ZERO,
                white_list_pct,
                notes,
            };
            if relevant < Decimal::ZERO {
                // Anche le minusvalenze da ETF (RC) sono redditi diversi: vanno nello zainetto.
                op.loss_added_eur = -relevant;
                self.add_loss(basket, fiscal_date.year(), -relevant);
            } else if relevant > Decimal::ZERO {
                if category != TaxCategory::RC {
                    op.losses_used = self.use_losses(rules, basket, fiscal_date, relevant);
                }
                let used: Decimal = op.losses_used.iter().map(|u| u.amount_eur).sum();
                op.taxable_eur = relevant - used;
                op.tax_eur = round_tax(op.taxable_eur * rate / dec!(100));
            }
            self.operations.push(op);
        }

        if let Event::Dividend {
            instrument,
            gross_eur,
            foreign_withholding_eur,
        } = &r.event
        {
            let category = category_of(instrument)?;
            let rate = rules.rate_pct(category.basket(), r.date)?;
            // In amministrato il 26% si applica al netto frontiera (dopo la ritenuta estera).
            let taxable = round_cents(gross_eur - foreign_withholding_eur);
            self.operations.push(TaxOperation {
                seq: r.seq,
                date: r.date,
                trade_date: r.date,
                instrument: instrument.clone(),
                category,
                kind: OperationKind::Dividend,
                income_eur: taxable,
                losses_used: Vec::new(),
                taxable_eur: taxable,
                rate_pct: rate,
                tax_eur: round_tax(taxable * rate / dec!(100)),
                loss_added_eur: Decimal::ZERO,
                white_list_pct: None,
                notes: Vec::new(),
            });
        }
        Ok(())
    }

    fn zainetto_at(&self, rules: &TaxRules, date: NaiveDate) -> Vec<ZainettoEntry> {
        self.zainetto
            .iter()
            .filter(|(&(_, y), v)| !v.is_zero() && rules.loss_expiry(y) >= date)
            .map(|(&(basket, origin_year), &residual_eur)| ZainettoEntry {
                basket,
                origin_year,
                expires_on: rules.loss_expiry(origin_year),
                residual_eur,
            })
            .collect()
    }
}

/// Report fiscale dell'anno `year` per i record di un conto (in ordine di `seq`).
pub fn report(
    records: &[Record],
    rules: &TaxRules,
    instruments: &BTreeMap<String, TaxCategory>,
    year: i32,
) -> Result<TaxReport, TaxError> {
    let year_end = NaiveDate::from_ymd_opt(year, 12, 31).expect("data valida");
    let mut engine = TaxEngine::default();
    let mut withheld = Decimal::ZERO;
    let mut stamp = Decimal::ZERO;
    for r in records.iter().filter(|r| r.date <= year_end) {
        engine.process(r, rules, instruments)?;
        if r.date.year() == year {
            match &r.event {
                Event::TaxWithheld { amount_eur, .. } => withheld += amount_eur,
                Event::StampDuty { amount_eur } => stamp += amount_eur,
                _ => {}
            }
        }
    }

    let mut sales: BTreeMap<TaxCategory, CategorySummary> = BTreeMap::new();
    let mut dividends = DividendSummary::default();
    let operations: Vec<TaxOperation> = engine
        .operations
        .iter()
        .filter(|o| o.date.year() == year)
        .cloned()
        .collect();
    for o in &operations {
        match o.kind {
            OperationKind::Sale => {
                let s = sales.entry(o.category).or_default();
                if o.income_eur > Decimal::ZERO {
                    s.gains_eur += o.income_eur;
                } else {
                    s.losses_eur -= o.income_eur;
                }
                s.losses_used_eur += o.losses_used.iter().map(|u| u.amount_eur).sum::<Decimal>();
                s.taxable_eur += o.taxable_eur;
                s.tax_eur += o.tax_eur;
            }
            OperationKind::Dividend => {
                dividends.taxable_eur += o.taxable_eur;
                dividends.tax_eur += o.tax_eur;
            }
        }
    }
    for r in records.iter().filter(|r| r.date.year() == year) {
        if let Event::Dividend {
            gross_eur,
            foreign_withholding_eur,
            ..
        } = &r.event
        {
            dividends.gross_eur += gross_eur;
            dividends.foreign_withholding_eur += foreign_withholding_eur;
        }
    }

    let tax_estimated: Decimal =
        sales.values().map(|s| s.tax_eur).sum::<Decimal>() + dividends.tax_eur;
    let zainetto = engine.zainetto_at(rules, year_end);
    let expiring: Decimal = zainetto
        .iter()
        .filter(|z| z.expires_on == year_end)
        .map(|z| z.residual_eur)
        .sum();
    let start = NaiveDate::from_ymd_opt(year, 1, 1).expect("data valida");
    let expired: Decimal = engine
        .zainetto
        .iter()
        .filter(|(&(_, y), _)| {
            rules.loss_expiry(y) < start && rules.loss_expiry(y).year() == year - 1
        })
        .map(|(_, v)| *v)
        .sum();

    let mut warnings: Vec<String> = operations.iter().flat_map(|o| o.notes.clone()).collect();
    if expiring > Decimal::ZERO {
        warnings.push(format!(
            "{expiring} € di minusvalenze scadono il {year_end}: valuta di realizzare plusvalenze RD compensabili"
        ));
    }
    if expired > Decimal::ZERO {
        warnings.push(format!(
            "{expired} € di minusvalenze sono scadute il 31/12/{} senza essere usate",
            year - 1
        ));
    }
    let difference = tax_estimated - withheld;
    if !difference.is_zero()
        && records
            .iter()
            .any(|r| matches!(r.event, Event::TaxWithheld { .. }))
    {
        warnings.push(format!(
            "differenza di {difference} € tra imposta stimata e trattenuta dal broker: da spiegare"
        ));
    }

    Ok(TaxReport {
        account: records
            .first()
            .map(|r| r.account.clone())
            .unwrap_or_default(),
        year,
        rules_verified_on: rules.verified_on,
        sales,
        dividends,
        tax_estimated_eur: tax_estimated,
        tax_withheld_by_broker_eur: withheld,
        difference_eur: difference,
        stamp_duty_charged_eur: stamp,
        zainetto,
        zainetto_expiring_eur: expiring,
        zainetto_expired_eur: expired,
        operations,
        warnings,
        disclaimer: DISCLAIMER.to_string(),
    })
}

/// Imposta che il broker dovrebbe trattenere per un singolo record, data la storia precedente.
/// Serve al simulatore (M3) per generare gli eventi `TaxWithheld` come farebbe il broker.
pub fn tax_due_for_last(
    records: &[Record],
    rules: &TaxRules,
    instruments: &BTreeMap<String, TaxCategory>,
) -> Result<Decimal, TaxError> {
    let Some(last) = records.last() else {
        return Ok(Decimal::ZERO);
    };
    let mut engine = TaxEngine::default();
    for r in records {
        engine.process(r, rules, instruments)?;
    }
    Ok(engine
        .operations
        .iter()
        .filter(|o| o.seq == last.seq)
        .map(|o| o.tax_eur)
        .sum())
}

/// Stima del bollo: somma giornaliera di valore × aliquota / giorni dell'anno.
/// `daily_values` contiene il valore del dossier per ogni giorno di calendario considerato.
pub fn stamp_duty_estimate(rules: &TaxRules, daily_values: &[(NaiveDate, Decimal)]) -> Decimal {
    let total: Decimal = daily_values
        .iter()
        .map(|(d, v)| {
            let days = if NaiveDate::from_ymd_opt(d.year(), 2, 29).is_some() {
                366
            } else {
                365
            };
            *v * rules.stamp_duty_pct_per_year / dec!(100) / Decimal::from(days)
        })
        .sum();
    round_cents(total)
}
