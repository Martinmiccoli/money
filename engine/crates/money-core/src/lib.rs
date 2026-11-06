//! `money-core`: guardrails, rischio, costi e fisco.
//!
//! È l'unica fonte di verità usata da backtest (via PyO3), paper e live.
//! Vedi `docs/02-progettazione/guardrails.md`.

pub mod config;
pub mod guardrails;
pub mod risk;
pub mod types;

#[cfg(test)]
mod tests;
