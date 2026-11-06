//! Configurazione dei guardrails (`config/guardrails.toml`) e sua validazione.
//!
//! I limiti `HARD_*` sono tetti codificati: nemmeno modificando il file di
//! configurazione si possono superare. Allentarli richiede una modifica al codice.

use serde::Deserialize;
use std::{collections::BTreeSet, path::Path};
use thiserror::Error;

use crate::types::{AssetClass, Mode};

/// Tetti massimi non superabili da configurazione.
pub const HARD_MAX_SOFT_STOP_PCT: f64 = 25.0;
pub const HARD_MAX_KILL_PCT: f64 = 60.0;
pub const HARD_MAX_COST_RATIO_PCT: f64 = 5.0;
pub const HARD_MIN_EDGE_TO_COST: f64 = 1.0;
pub const HARD_MAX_ORDERS_PER_DAY: u32 = 20;
pub const HARD_MAX_SINGLE_STOCK_PCT: f64 = 50.0;
pub const HARD_MAX_CRYPTO_PCT: f64 = 30.0;
pub const HARD_MAX_SLIPPAGE_PCT: f64 = 5.0;
pub const HARD_MAX_TTL_HOURS: u32 = 168;
pub const HARD_MAX_STALENESS_HOURS: f64 = 72.0;

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct GuardrailsConfig {
    pub mode: Mode,
    #[serde(default)]
    pub validation_report_sha256: String,
    pub capital: Capital,
    pub drawdown: Drawdown,
    pub orders: Orders,
    pub positions: Positions,
    pub hybrid: Hybrid,
    pub data: Data,
    pub instruments: Instruments,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Capital {
    pub net_deposits_eur: f64,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Drawdown {
    pub soft_stop_pct: f64,
    pub hard_kill_pct: f64,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Orders {
    pub max_cost_ratio_pct: f64,
    pub min_edge_to_cost: f64,
    pub max_orders_per_day: u32,
    pub max_orders_per_week: u32,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Positions {
    pub max_single_stock_pct: f64,
    pub max_broad_etf_pct: f64,
    pub max_crypto_etp_total_pct: f64,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Hybrid {
    pub max_limit_slippage_pct: f64,
    pub proposal_ttl_hours: u32,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Data {
    pub max_staleness_hours: f64,
}

#[derive(Debug, Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Instruments {
    pub real_money: BTreeSet<AssetClass>,
    pub paper_only: BTreeSet<AssetClass>,
}

#[derive(Debug, Error)]
pub enum ConfigError {
    #[error("impossibile leggere la configurazione: {0}")]
    Io(#[from] std::io::Error),
    #[error("configurazione non valida (sintassi): {0}")]
    Parse(#[from] toml::de::Error),
    #[error("configurazione non valida: {0}")]
    Invalid(String),
}

fn check(cond: bool, msg: impl Into<String>, errs: &mut Vec<String>) {
    if !cond {
        errs.push(msg.into());
    }
}

fn in_range(v: f64, lo: f64, hi: f64) -> bool {
    v.is_finite() && v >= lo && v <= hi
}

impl GuardrailsConfig {
    pub fn load(path: impl AsRef<Path>) -> Result<Self, ConfigError> {
        Self::from_toml_str(&std::fs::read_to_string(path)?)
    }

    pub fn from_toml_str(s: &str) -> Result<Self, ConfigError> {
        let cfg: Self = toml::from_str(s)?;
        cfg.validate()?;
        Ok(cfg)
    }

    /// Valida tutti i valori. Restituisce tutti gli errori insieme, non solo il primo.
    pub fn validate(&self) -> Result<(), ConfigError> {
        let mut e = Vec::new();

        check(
            in_range(self.capital.net_deposits_eur, 0.01, 1e9),
            "capital.net_deposits_eur deve essere > 0",
            &mut e,
        );

        let d = &self.drawdown;
        check(
            in_range(d.soft_stop_pct, 1.0, HARD_MAX_SOFT_STOP_PCT),
            format!("drawdown.soft_stop_pct deve stare in [1, {HARD_MAX_SOFT_STOP_PCT}]"),
            &mut e,
        );
        check(
            in_range(d.hard_kill_pct, d.soft_stop_pct, HARD_MAX_KILL_PCT),
            format!("drawdown.hard_kill_pct deve stare in [soft_stop_pct, {HARD_MAX_KILL_PCT}]"),
            &mut e,
        );

        let o = &self.orders;
        check(
            in_range(o.max_cost_ratio_pct, 0.0, HARD_MAX_COST_RATIO_PCT),
            format!("orders.max_cost_ratio_pct deve stare in [0, {HARD_MAX_COST_RATIO_PCT}]"),
            &mut e,
        );
        check(
            in_range(o.min_edge_to_cost, HARD_MIN_EDGE_TO_COST, 100.0),
            format!("orders.min_edge_to_cost deve essere >= {HARD_MIN_EDGE_TO_COST}"),
            &mut e,
        );
        check(
            (1..=HARD_MAX_ORDERS_PER_DAY).contains(&o.max_orders_per_day),
            format!("orders.max_orders_per_day deve stare in [1, {HARD_MAX_ORDERS_PER_DAY}]"),
            &mut e,
        );
        check(
            o.max_orders_per_week >= o.max_orders_per_day
                && o.max_orders_per_week <= HARD_MAX_ORDERS_PER_DAY * 5,
            "orders.max_orders_per_week deve stare in [max_orders_per_day, 5 * tetto giornaliero]",
            &mut e,
        );

        let p = &self.positions;
        check(
            in_range(p.max_single_stock_pct, 0.0, HARD_MAX_SINGLE_STOCK_PCT),
            format!(
                "positions.max_single_stock_pct deve stare in [0, {HARD_MAX_SINGLE_STOCK_PCT}]"
            ),
            &mut e,
        );
        check(
            in_range(p.max_broad_etf_pct, 0.0, 100.0),
            "positions.max_broad_etf_pct deve stare in [0, 100]",
            &mut e,
        );
        check(
            in_range(p.max_crypto_etp_total_pct, 0.0, HARD_MAX_CRYPTO_PCT),
            format!("positions.max_crypto_etp_total_pct deve stare in [0, {HARD_MAX_CRYPTO_PCT}]"),
            &mut e,
        );

        let h = &self.hybrid;
        check(
            in_range(h.max_limit_slippage_pct, 0.0, HARD_MAX_SLIPPAGE_PCT),
            format!("hybrid.max_limit_slippage_pct deve stare in [0, {HARD_MAX_SLIPPAGE_PCT}]"),
            &mut e,
        );
        check(
            (1..=HARD_MAX_TTL_HOURS).contains(&h.proposal_ttl_hours),
            format!("hybrid.proposal_ttl_hours deve stare in [1, {HARD_MAX_TTL_HOURS}]"),
            &mut e,
        );

        check(
            in_range(self.data.max_staleness_hours, 1.0, HARD_MAX_STALENESS_HOURS),
            format!("data.max_staleness_hours deve stare in [1, {HARD_MAX_STALENESS_HOURS}]"),
            &mut e,
        );

        // G-03 / G-13: le crypto spot non possono mai andare con soldi veri (scelta di progetto).
        check(
            !self
                .instruments
                .real_money
                .contains(&AssetClass::CryptoSpot),
            "instruments.real_money non può contenere crypto_spot (ADR-003)",
            &mut e,
        );
        check(
            !self.instruments.real_money.contains(&AssetClass::EtfUs),
            "instruments.real_money non può contenere etf_us (PRIIPs/KID, G-13)",
            &mut e,
        );
        check(
            self.instruments
                .real_money
                .is_disjoint(&self.instruments.paper_only),
            "una classe non può stare sia in real_money sia in paper_only",
            &mut e,
        );

        // G-15: i soldi veri richiedono un report di validazione referenziato per hash.
        if self.mode.is_real_money() {
            let h = &self.validation_report_sha256;
            check(
                h.len() == 64 && h.chars().all(|c| c.is_ascii_hexdigit()),
                "mode hybrid/live richiede validation_report_sha256 (64 caratteri hex) — G-15",
                &mut e,
            );
        }

        if e.is_empty() {
            Ok(())
        } else {
            Err(ConfigError::Invalid(e.join("; ")))
        }
    }

    /// G-13: la classe di strumento è ammessa nella modalità corrente?
    pub fn asset_allowed(&self, class: AssetClass) -> bool {
        self.instruments.real_money.contains(&class)
            || (!self.mode.is_real_money() && self.instruments.paper_only.contains(&class))
    }
}
