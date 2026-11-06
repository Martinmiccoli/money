//! Tipi di dominio condivisi.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Mode {
    /// Soldi finti, esecuzione automatica.
    Paper,
    /// Soldi veri: proposte notificate ed eseguite dall'utente con un tap.
    Hybrid,
    /// Soldi veri, esecuzione automatica via API.
    Live,
}

impl Mode {
    pub fn is_real_money(self) -> bool {
        !matches!(self, Mode::Paper)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum AssetClass {
    StockUs,
    EtfUcits,
    EtfUs,
    CryptoEtp,
    CryptoSpot,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Side {
    Buy,
    Sell,
}

/// Richiesta di ordine prima dei controlli dei guardrails.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct OrderRequest {
    pub instrument: String,
    pub asset_class: AssetClass,
    pub side: Side,
    /// Controvalore in EUR.
    pub notional_eur: f64,
    /// Costo stimato del singolo lato: commissione + spread + tasse di transazione (EUR).
    pub est_cost_eur: f64,
    /// Rendimento atteso del segnale, in % (obbligatorio per gli acquisti, G-06).
    pub expected_edge_pct: Option<f64>,
    /// Prezzo di riferimento al momento della decisione.
    pub ref_price: f64,
    /// Prezzo limite (obbligatorio in modalità hybrid, G-09).
    pub limit_price: Option<f64>,
    /// Validità della proposta in ore (obbligatoria in modalità hybrid, G-09).
    pub valid_for_hours: Option<u32>,
}

/// Fotografia del portafoglio al momento del controllo.
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct PortfolioSnapshot {
    pub equity_eur: f64,
    pub cash_eur: f64,
    /// Controvalore per strumento.
    pub positions: HashMap<String, Position>,
    pub orders_today: u32,
    pub orders_this_week: u32,
    /// Età in ore del dato di mercato più vecchio usato per la decisione.
    pub data_age_hours: f64,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Position {
    pub asset_class: AssetClass,
    pub value_eur: f64,
}

impl PortfolioSnapshot {
    pub fn position_value(&self, instrument: &str) -> f64 {
        self.positions.get(instrument).map_or(0.0, |p| p.value_eur)
    }

    pub fn class_value(&self, class: AssetClass) -> f64 {
        self.positions
            .values()
            .filter(|p| p.asset_class == class)
            .map(|p| p.value_eur)
            .sum()
    }
}
