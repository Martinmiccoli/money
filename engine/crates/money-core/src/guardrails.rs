//! Controllo pre-trade: ogni ordine passa da [`check_order`] prima dell'esecuzione,
//! in qualsiasi modalità (backtest, paper, hybrid, live).
//!
//! Le **vendite** che riducono una posizione esistente sono esenti dai limiti di costo,
//! edge e frequenza (G-05, G-06, G-07): uscire dal rischio deve essere sempre possibile.

use std::fmt;

use crate::{
    config::GuardrailsConfig,
    risk::RiskState,
    types::{AssetClass, Mode, OrderRequest, PortfolioSnapshot, Side},
};

#[derive(Debug, Clone, PartialEq)]
pub enum Violation {
    /// G-01
    SoftStopActive,
    /// G-02
    KillSwitchActive,
    /// G-03: vendita oltre la posizione posseduta (short).
    ShortNotAllowed {
        held_eur: f64,
        requested_eur: f64,
    },
    /// G-04
    InsufficientCash {
        cash_eur: f64,
        required_eur: f64,
    },
    /// G-05
    CostTooHigh {
        cost_pct: f64,
        max_pct: f64,
    },
    /// G-06
    MissingEdge,
    EdgeBelowCost {
        edge_pct: f64,
        required_pct: f64,
    },
    /// G-07
    DailyOrderLimit {
        max: u32,
    },
    WeeklyOrderLimit {
        max: u32,
    },
    /// G-08
    PositionTooLarge {
        class: AssetClass,
        weight_pct: f64,
        max_pct: f64,
    },
    /// G-09
    MissingLimitPrice,
    LimitTooFar {
        slippage_pct: f64,
        max_pct: f64,
    },
    MissingExpiry,
    ExpiryTooLong {
        hours: u32,
        max: u32,
    },
    /// G-10
    StaleData {
        age_hours: f64,
        max_hours: f64,
    },
    /// G-13
    AssetNotAllowed {
        class: AssetClass,
        mode: Mode,
    },
    /// Input non valido (NaN, valori negativi...).
    InvalidInput(&'static str),
}

impl Violation {
    pub fn code(&self) -> &'static str {
        use Violation::*;
        match self {
            SoftStopActive => "G-01",
            KillSwitchActive => "G-02",
            ShortNotAllowed { .. } => "G-03",
            InsufficientCash { .. } => "G-04",
            CostTooHigh { .. } => "G-05",
            MissingEdge | EdgeBelowCost { .. } => "G-06",
            DailyOrderLimit { .. } | WeeklyOrderLimit { .. } => "G-07",
            PositionTooLarge { .. } => "G-08",
            MissingLimitPrice | LimitTooFar { .. } | MissingExpiry | ExpiryTooLong { .. } => "G-09",
            StaleData { .. } => "G-10",
            AssetNotAllowed { .. } => "G-13",
            InvalidInput(_) => "INPUT",
        }
    }
}

impl fmt::Display for Violation {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "[{}] {:?}", self.code(), self)
    }
}

fn finite_nonneg(v: f64) -> bool {
    v.is_finite() && v >= 0.0
}

/// Controlla un ordine contro tutti i guardrails. Restituisce **tutte** le violazioni trovate.
pub fn check_order(
    cfg: &GuardrailsConfig,
    risk: RiskState,
    pf: &PortfolioSnapshot,
    o: &OrderRequest,
) -> Result<(), Vec<Violation>> {
    let mut v = Vec::new();

    // Validazione degli input: un dato rotto non deve mai trasformarsi in un ordine.
    if !(o.notional_eur.is_finite() && o.notional_eur > 0.0) {
        v.push(Violation::InvalidInput("notional_eur deve essere > 0"));
    }
    if !finite_nonneg(o.est_cost_eur) {
        v.push(Violation::InvalidInput("est_cost_eur deve essere >= 0"));
    }
    if !(o.ref_price.is_finite() && o.ref_price > 0.0) {
        v.push(Violation::InvalidInput("ref_price deve essere > 0"));
    }
    if !(pf.equity_eur.is_finite() && pf.equity_eur > 0.0) || !finite_nonneg(pf.cash_eur) {
        v.push(Violation::InvalidInput(
            "snapshot del portafoglio non valido",
        ));
    }
    if !v.is_empty() {
        return Err(v);
    }

    // G-02 / G-01
    match (risk, o.side) {
        (RiskState::Locked, _) => v.push(Violation::KillSwitchActive),
        (RiskState::Suspended, Side::Buy) => v.push(Violation::SoftStopActive),
        _ => {}
    }

    // G-13
    if !cfg.asset_allowed(o.asset_class) {
        v.push(Violation::AssetNotAllowed {
            class: o.asset_class,
            mode: cfg.mode,
        });
    }

    // G-10: con dati vecchi non si opera, nemmeno in vendita (la valutazione sarebbe falsa).
    if !(pf.data_age_hours.is_finite() && pf.data_age_hours <= cfg.data.max_staleness_hours) {
        v.push(Violation::StaleData {
            age_hours: pf.data_age_hours,
            max_hours: cfg.data.max_staleness_hours,
        });
    }

    let cost_pct = o.est_cost_eur / o.notional_eur * 100.0;

    match o.side {
        Side::Buy => {
            // G-04
            let required = o.notional_eur + o.est_cost_eur;
            if required > pf.cash_eur {
                v.push(Violation::InsufficientCash {
                    cash_eur: pf.cash_eur,
                    required_eur: required,
                });
            }
            // G-05
            if cost_pct > cfg.orders.max_cost_ratio_pct {
                v.push(Violation::CostTooHigh {
                    cost_pct,
                    max_pct: cfg.orders.max_cost_ratio_pct,
                });
            }
            // G-06: rendimento atteso >= k * costo round-trip (acquisto + vendita).
            match o.expected_edge_pct {
                None => v.push(Violation::MissingEdge),
                Some(edge) => {
                    let required_pct = cfg.orders.min_edge_to_cost * 2.0 * cost_pct;
                    if !edge.is_finite() || edge < required_pct {
                        v.push(Violation::EdgeBelowCost {
                            edge_pct: edge,
                            required_pct,
                        });
                    }
                }
            }
            // G-07
            if pf.orders_today >= cfg.orders.max_orders_per_day {
                v.push(Violation::DailyOrderLimit {
                    max: cfg.orders.max_orders_per_day,
                });
            }
            if pf.orders_this_week >= cfg.orders.max_orders_per_week {
                v.push(Violation::WeeklyOrderLimit {
                    max: cfg.orders.max_orders_per_week,
                });
            }
            // G-08: peso dopo l'acquisto.
            let p = &cfg.positions;
            let (after, max_pct) = match o.asset_class {
                AssetClass::StockUs => (
                    pf.position_value(&o.instrument) + o.notional_eur,
                    p.max_single_stock_pct,
                ),
                AssetClass::EtfUcits | AssetClass::EtfUs => (
                    pf.position_value(&o.instrument) + o.notional_eur,
                    p.max_broad_etf_pct,
                ),
                AssetClass::CryptoEtp | AssetClass::CryptoSpot => (
                    pf.class_value(AssetClass::CryptoEtp)
                        + pf.class_value(AssetClass::CryptoSpot)
                        + o.notional_eur,
                    p.max_crypto_etp_total_pct,
                ),
            };
            let weight_pct = after / pf.equity_eur * 100.0;
            if weight_pct > max_pct {
                v.push(Violation::PositionTooLarge {
                    class: o.asset_class,
                    weight_pct,
                    max_pct,
                });
            }
        }
        Side::Sell => {
            // G-03: niente short.
            let held = pf.position_value(&o.instrument);
            if o.notional_eur > held * 1.0001 {
                v.push(Violation::ShortNotAllowed {
                    held_eur: held,
                    requested_eur: o.notional_eur,
                });
            }
        }
    }

    // G-09: le proposte hybrid hanno sempre prezzo limite e scadenza.
    if cfg.mode == Mode::Hybrid {
        match o.limit_price {
            None => v.push(Violation::MissingLimitPrice),
            Some(lp) => {
                let slippage_pct = (lp - o.ref_price).abs() / o.ref_price * 100.0;
                if !slippage_pct.is_finite() || slippage_pct > cfg.hybrid.max_limit_slippage_pct {
                    v.push(Violation::LimitTooFar {
                        slippage_pct,
                        max_pct: cfg.hybrid.max_limit_slippage_pct,
                    });
                }
            }
        }
        match o.valid_for_hours {
            None => v.push(Violation::MissingExpiry),
            Some(h) if h == 0 || h > cfg.hybrid.proposal_ttl_hours => {
                v.push(Violation::ExpiryTooLong {
                    hours: h,
                    max: cfg.hybrid.proposal_ttl_hours,
                })
            }
            _ => {}
        }
    }

    if v.is_empty() {
        Ok(())
    } else {
        Err(v)
    }
}
