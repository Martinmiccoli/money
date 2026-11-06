//! Modello dei costi di transazione (3.4).
//!
//! Lo **stesso** codice calcola i costi in backtest, paper e live: se il backtest
//! pagasse costi diversi da quelli reali, i suoi risultati mentirebbero.
//!
//! Costo di un lato = commissione + metà spread + FTT (solo sugli acquisti soggetti).
//! Lo spread non è un addebito separato: peggiora il prezzo di esecuzione.

use std::{collections::BTreeMap, path::Path};

use rust_decimal::{Decimal, RoundingStrategy};
use rust_decimal_macros::dec;
use serde::{Deserialize, Serialize};
use thiserror::Error;

use crate::types::{AssetClass, Side};

/// Tetti di sanità: un profilo oltre questi valori è quasi certamente un errore di battitura.
const MAX_FEE_EUR: Decimal = dec!(50);
const MAX_SPREAD_BPS: Decimal = dec!(1000);
const MAX_FTT_BPS: Decimal = dec!(100);
const ALL_CLASSES: [AssetClass; 5] = [
    AssetClass::StockUs,
    AssetClass::EtfUcits,
    AssetClass::EtfUs,
    AssetClass::CryptoEtp,
    AssetClass::CryptoSpot,
];

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct BrokerProfile {
    pub name: String,
    pub fee_per_order_eur: Decimal,
    pub fee_savings_plan_eur: Decimal,
    pub ftt_it_bps: Decimal,
    /// Spread bid/ask completo per classe, in punti base.
    pub spread_bps: BTreeMap<AssetClass, Decimal>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum OrderKind {
    /// Ordine singolo: commissione piena.
    Regular,
    /// Esecuzione di un piano di accumulo.
    SavingsPlan,
}

/// Esito del calcolo dei costi per un lato.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Quote {
    /// Prezzo di esecuzione stimato (riferimento ± metà spread).
    pub fill_price_eur: Decimal,
    pub commission_eur: Decimal,
    /// Costo implicito dello spread: |fill - riferimento| × quantità.
    pub spread_cost_eur: Decimal,
    pub ftt_eur: Decimal,
}

impl Quote {
    pub fn total_cost_eur(&self) -> Decimal {
        self.commission_eur + self.spread_cost_eur + self.ftt_eur
    }
}

#[derive(Debug, Error)]
pub enum CostError {
    #[error("impossibile leggere il profilo costi: {0}")]
    Io(#[from] std::io::Error),
    #[error("profilo costi non valido (sintassi): {0}")]
    Parse(#[from] toml::de::Error),
    #[error("profilo costi non valido: {0}")]
    Invalid(String),
    #[error("input non valido: {0}")]
    Input(&'static str),
}

/// Arrotonda al centesimo (metà lontano da zero, come gli addebiti bancari).
pub fn round_cents(v: Decimal) -> Decimal {
    v.round_dp_with_strategy(2, RoundingStrategy::MidpointAwayFromZero)
}

impl BrokerProfile {
    pub fn load(path: impl AsRef<Path>) -> Result<Self, CostError> {
        Self::from_toml_str(&std::fs::read_to_string(path)?)
    }

    pub fn from_toml_str(s: &str) -> Result<Self, CostError> {
        let p: Self = toml::from_str(s)?;
        p.validate()?;
        Ok(p)
    }

    pub fn validate(&self) -> Result<(), CostError> {
        let mut e = Vec::new();
        let in_range = |v: Decimal, max: Decimal| v >= Decimal::ZERO && v <= max;
        if !in_range(self.fee_per_order_eur, MAX_FEE_EUR) {
            e.push(format!(
                "fee_per_order_eur deve stare in [0, {MAX_FEE_EUR}]"
            ));
        }
        if !in_range(self.fee_savings_plan_eur, MAX_FEE_EUR) {
            e.push(format!(
                "fee_savings_plan_eur deve stare in [0, {MAX_FEE_EUR}]"
            ));
        }
        if !in_range(self.ftt_it_bps, MAX_FTT_BPS) {
            e.push(format!("ftt_it_bps deve stare in [0, {MAX_FTT_BPS}]"));
        }
        for c in ALL_CLASSES {
            match self.spread_bps.get(&c) {
                None => e.push(format!("spread_bps manca per la classe {c:?}")),
                Some(v) if !in_range(*v, MAX_SPREAD_BPS) => e.push(format!(
                    "spread_bps[{c:?}] deve stare in [0, {MAX_SPREAD_BPS}]"
                )),
                _ => {}
            }
        }
        if e.is_empty() {
            Ok(())
        } else {
            Err(CostError::Invalid(e.join("; ")))
        }
    }

    fn half_spread(&self, class: AssetClass) -> Decimal {
        // validate() garantisce che ogni classe sia presente.
        self.spread_bps[&class] / dec!(20000)
    }

    /// Costi di un lato per `qty` unità al prezzo di riferimento `ref_price_eur`.
    /// `ftt_liable`: azione italiana con capitalizzazione >= 500 M€ (FTT sugli acquisti).
    pub fn quote(
        &self,
        class: AssetClass,
        side: Side,
        kind: OrderKind,
        qty: Decimal,
        ref_price_eur: Decimal,
        ftt_liable: bool,
    ) -> Result<Quote, CostError> {
        if qty <= Decimal::ZERO {
            return Err(CostError::Input("qty deve essere > 0"));
        }
        if ref_price_eur <= Decimal::ZERO {
            return Err(CostError::Input("ref_price_eur deve essere > 0"));
        }
        let hs = self.half_spread(class);
        let fill = match side {
            Side::Buy => ref_price_eur * (Decimal::ONE + hs),
            Side::Sell => ref_price_eur * (Decimal::ONE - hs),
        };
        let commission = match kind {
            OrderKind::Regular => self.fee_per_order_eur,
            OrderKind::SavingsPlan => self.fee_savings_plan_eur,
        };
        let ftt = if ftt_liable && side == Side::Buy {
            round_cents(qty * fill * self.ftt_it_bps / dec!(10000))
        } else {
            Decimal::ZERO
        };
        Ok(Quote {
            fill_price_eur: fill,
            commission_eur: commission,
            spread_cost_eur: (fill - ref_price_eur).abs() * qty,
            ftt_eur: ftt,
        })
    }

    /// Stima del costo di un lato per un controvalore in EUR (per i guardrails G-05/G-06).
    pub fn est_side_cost_eur(
        &self,
        class: AssetClass,
        side: Side,
        kind: OrderKind,
        notional_eur: Decimal,
        ftt_liable: bool,
    ) -> Result<Decimal, CostError> {
        if notional_eur <= Decimal::ZERO {
            return Err(CostError::Input("notional_eur deve essere > 0"));
        }
        // Con prezzo di riferimento 1 la quantità coincide con il controvalore.
        Ok(self
            .quote(class, side, kind, notional_eur, Decimal::ONE, ftt_liable)?
            .total_cost_eur())
    }
}
