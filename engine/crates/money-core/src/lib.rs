//! `money-core`: guardrails, rischio, costi, ledger e fisco.
//!
//! È l'unica fonte di verità usata da backtest (via PyO3), paper e live.
//! Vedi `docs/02-progettazione/guardrails.md` e `docs/03-system-design/`.

pub mod config;
pub mod costs;
pub mod guardrails;
pub mod ledger;
pub mod portfolio;
pub mod risk;
pub mod tax;
pub mod types;

#[cfg(test)]
mod tests;
#[cfg(test)]
mod tests_m2;
