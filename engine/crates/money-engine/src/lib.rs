//! `money-engine`: motore di esecuzione del paper trading (M6).
//!
//! Flusso: intenzioni d'ordine (Python) → guardrails (`money-core`, tipo `CheckedOrder`) →
//! adapter `SimBroker` (+ copia ombra su Alpaca Paper) → ledger append-only su Postgres.
//! **Non piazza mai ordini reali** (G-17): rifiuta di partire se la modalità non è `paper`.

pub mod alpaca;
pub mod plan;
pub mod store;

#[cfg(test)]
mod tests;
