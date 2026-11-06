//! Proiezione del portafoglio dagli eventi del ledger: cassa e posizioni a costo medio ponderato.
//!
//! Il costo fiscale di una posizione include le commissioni d'acquisto (oneri accessori).
//! In vendita, il ricavo fiscale è al netto della commissione. La Tobin tax (FTT) riduce la
//! cassa ma **non** il reddito: non è deducibile ai fini delle imposte sui redditi
//! (L. 228/2012, art. 1 c. 491 e seguenti; comma esatto da verificare, vedi `knowledge/fisco/`).
//! Il costo medio ponderato è il criterio del regime amministrato (art. 68 c. 6 TUIR,
//! art. 6 D.Lgs. 461/1997): vedi `knowledge/fisco/`.

use std::collections::BTreeMap;

use rust_decimal::Decimal;
use serde::{Deserialize, Serialize};
use thiserror::Error;

use crate::{ledger::Event, types::Side};

/// Precisione interna del costo residuo dopo una vendita parziale.
const COST_DP: u32 = 8;

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct Holding {
    pub qty: Decimal,
    /// Costo fiscale complessivo della quantità posseduta (oneri inclusi).
    pub cost_eur: Decimal,
}

impl Holding {
    pub fn avg_cost_eur(&self) -> Decimal {
        if self.qty.is_zero() {
            Decimal::ZERO
        } else {
            self.cost_eur / self.qty
        }
    }
}

/// Esito fiscale di una vendita: lo consuma il motore fiscale.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct Realization {
    pub instrument: String,
    pub qty: Decimal,
    /// Ricavo fiscale: quantità × prezzo − commissione (la FTT non è deducibile).
    pub proceeds_eur: Decimal,
    /// Costo fiscale della quantità venduta (costo medio ponderato).
    pub cost_eur: Decimal,
    pub gain_eur: Decimal,
}

#[derive(Debug, Clone, PartialEq, Error)]
pub enum ProjectionError {
    #[error("{0} deve essere > 0")]
    NotPositive(&'static str),
    #[error("{0} non può essere negativo")]
    Negative(&'static str),
    #[error("vendita di {requested} {instrument} ma ne possiedi {held} (G-03)")]
    Oversell {
        instrument: String,
        held: Decimal,
        requested: Decimal,
    },
    #[error("cassa insufficiente: servono {required} €, disponibili {available} € (G-04)")]
    InsufficientCash {
        available: Decimal,
        required: Decimal,
    },
    #[error("strumento vuoto")]
    EmptyInstrument,
}

#[derive(Debug, Clone, Default, PartialEq, Serialize, Deserialize)]
pub struct Portfolio {
    pub cash_eur: Decimal,
    /// Versamenti meno prelievi (base del kill switch G-02).
    pub net_deposits_eur: Decimal,
    pub holdings: BTreeMap<String, Holding>,
}

fn positive(v: Decimal, what: &'static str) -> Result<(), ProjectionError> {
    if v > Decimal::ZERO {
        Ok(())
    } else {
        Err(ProjectionError::NotPositive(what))
    }
}

fn non_negative(v: Decimal, what: &'static str) -> Result<(), ProjectionError> {
    if v >= Decimal::ZERO {
        Ok(())
    } else {
        Err(ProjectionError::Negative(what))
    }
}

impl Portfolio {
    /// Applica un evento. In caso di errore lo stato non cambia.
    pub fn apply(&mut self, e: &Event) -> Result<Option<Realization>, ProjectionError> {
        match e {
            Event::Deposit { amount_eur } => {
                positive(*amount_eur, "amount_eur")?;
                self.cash_eur += amount_eur;
                self.net_deposits_eur += amount_eur;
                Ok(None)
            }
            Event::Withdrawal { amount_eur } => {
                positive(*amount_eur, "amount_eur")?;
                self.require_cash(*amount_eur)?;
                self.cash_eur -= amount_eur;
                self.net_deposits_eur -= amount_eur;
                Ok(None)
            }
            Event::Fill {
                instrument,
                side,
                qty,
                price_eur,
                commission_eur,
                transaction_tax_eur,
                ..
            } => {
                if instrument.trim().is_empty() {
                    return Err(ProjectionError::EmptyInstrument);
                }
                positive(*qty, "qty")?;
                positive(*price_eur, "price_eur")?;
                non_negative(*commission_eur, "commission_eur")?;
                non_negative(*transaction_tax_eur, "transaction_tax_eur")?;
                let gross = qty * price_eur;
                match side {
                    Side::Buy => {
                        let fiscal_cost = gross + commission_eur;
                        let cash_out = fiscal_cost + transaction_tax_eur;
                        self.require_cash(cash_out)?;
                        self.cash_eur -= cash_out;
                        let h = self.holdings.entry(instrument.clone()).or_default();
                        h.qty += qty;
                        h.cost_eur += fiscal_cost;
                        Ok(None)
                    }
                    Side::Sell => {
                        let held = self
                            .holdings
                            .get(instrument)
                            .map_or(Decimal::ZERO, |h| h.qty);
                        if *qty > held {
                            return Err(ProjectionError::Oversell {
                                instrument: instrument.clone(),
                                held,
                                requested: *qty,
                            });
                        }
                        let proceeds = gross - commission_eur;
                        let cash_in = proceeds - transaction_tax_eur;
                        // Spese superiori al ricavo lordo: serve cassa per coprirle.
                        if cash_in < Decimal::ZERO {
                            self.require_cash(-cash_in)?;
                        }
                        let h = self
                            .holdings
                            .get_mut(instrument)
                            .expect("controllato sopra");
                        let cost = if *qty == h.qty {
                            h.cost_eur
                        } else {
                            (h.cost_eur * qty / h.qty).round_dp(COST_DP)
                        };
                        h.qty -= qty;
                        h.cost_eur -= cost;
                        if h.qty.is_zero() {
                            self.holdings.remove(instrument);
                        }
                        self.cash_eur += cash_in;
                        Ok(Some(Realization {
                            instrument: instrument.clone(),
                            qty: *qty,
                            proceeds_eur: proceeds,
                            cost_eur: cost,
                            gain_eur: proceeds - cost,
                        }))
                    }
                }
            }
            Event::Dividend {
                instrument,
                gross_eur,
                foreign_withholding_eur,
            } => {
                if instrument.trim().is_empty() {
                    return Err(ProjectionError::EmptyInstrument);
                }
                positive(*gross_eur, "gross_eur")?;
                non_negative(*foreign_withholding_eur, "foreign_withholding_eur")?;
                if foreign_withholding_eur > gross_eur {
                    return Err(ProjectionError::Negative("dividendo netto"));
                }
                self.cash_eur += gross_eur - foreign_withholding_eur;
                Ok(None)
            }
            // Addebiti del broker: sono fatti, si registrano anche se la cassa va sotto zero
            // (la riconciliazione segnalerà la differenza).
            Event::TaxWithheld { amount_eur, .. } => {
                self.cash_eur -= amount_eur;
                Ok(None)
            }
            Event::StampDuty { amount_eur } => {
                non_negative(*amount_eur, "amount_eur")?;
                self.cash_eur -= amount_eur;
                Ok(None)
            }
            Event::Interest { amount_eur } => {
                positive(*amount_eur, "amount_eur")?;
                self.cash_eur += amount_eur;
                Ok(None)
            }
            Event::RiskStateChanged { .. }
            | Event::ConfigChanged { .. }
            | Event::Reconciliation { .. } => Ok(None),
        }
    }

    fn require_cash(&self, required: Decimal) -> Result<(), ProjectionError> {
        if required > self.cash_eur {
            Err(ProjectionError::InsufficientCash {
                available: self.cash_eur,
                required,
            })
        } else {
            Ok(())
        }
    }
}
