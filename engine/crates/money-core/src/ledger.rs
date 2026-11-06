//! Ledger append-only a catena di hash (3.3, G-16).
//!
//! Il ledger è la **verità contabile**: posizioni, cassa e tasse sono proiezioni
//! ricalcolate dagli eventi (vedi [`crate::portfolio`] e [`crate::tax`]).
//!
//! Ogni record contiene l'hash del precedente:
//! `hash = sha256(prev_hash ‖ json(corpo))`, dove il corpo è tutto il record tranne l'hash.
//! Modificare, togliere o riordinare un evento rompe la catena da quel punto in poi.
//!
//! Gli importi sono `Decimal` serializzati come **stringhe**, così il JSON è identico
//! byte per byte quando viene riletto dal database (jsonb conserva le stringhe).

use chrono::{DateTime, NaiveDate, Utc};
use rust_decimal::Decimal;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use thiserror::Error;

use crate::{
    portfolio::{Portfolio, ProjectionError},
    types::Side,
};

/// `prev_hash` del primo evento di ogni conto.
pub const GENESIS_HASH: &str = "0000000000000000000000000000000000000000000000000000000000000000";

/// Eventi contabili. Gli eventi del flusso delle proposte (3.5) si aggiungeranno nella M6/M7.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(tag = "kind", deny_unknown_fields)]
pub enum Event {
    Deposit {
        amount_eur: Decimal,
    },
    Withdrawal {
        amount_eur: Decimal,
    },
    /// Esecuzione (anche parziale) di un ordine.
    Fill {
        instrument: String,
        side: Side,
        qty: Decimal,
        /// Prezzo effettivo per unità, in EUR (spread incluso).
        price_eur: Decimal,
        commission_eur: Decimal,
        /// Tobin tax o altre imposte di transazione addebitate sull'operazione.
        #[serde(default)]
        transaction_tax_eur: Decimal,
        /// Prezzo di riferimento al momento della decisione (per calibrare lo spread).
        #[serde(default)]
        ref_price_eur: Option<Decimal>,
        #[serde(default)]
        venue: Option<String>,
        #[serde(default)]
        broker_order_id: Option<String>,
        /// Data di regolamento: è quella che fa fede per l'anno fiscale (circ. AdE 19/E/2014
        /// per gli OICR; per prudenza la usiamo per tutto). Se manca si stima T+2 lavorativi.
        #[serde(default)]
        settlement_date: Option<NaiveDate>,
        /// Solo vendite di ETF/OICR: % media dell'attivo in titoli di Stato "white list"
        /// pubblicata dall'emittente per il semestre (DM 13/12/2011). Riduce sia la
        /// plusvalenza sia la minusvalenza rilevante.
        #[serde(default)]
        white_list_pct: Option<Decimal>,
    },
    /// Dividendo accreditato. `foreign_withholding_eur` è la ritenuta estera (es. 15% USA).
    /// L'imposta italiana trattenuta dal broker è un evento `TaxWithheld` separato.
    Dividend {
        instrument: String,
        gross_eur: Decimal,
        foreign_withholding_eur: Decimal,
    },
    /// Imposta trattenuta (positiva) o restituita (negativa) dal broker in regime amministrato.
    TaxWithheld {
        amount_eur: Decimal,
        #[serde(default)]
        reference: Option<String>,
    },
    /// Imposta di bollo addebitata.
    StampDuty {
        amount_eur: Decimal,
    },
    /// Interessi lordi sulla liquidità (redditi di capitale: il broker trattiene il 26% con un
    /// evento `TaxWithheld` separato).
    Interest {
        amount_eur: Decimal,
    },
    RiskStateChanged {
        from: String,
        to: String,
        equity_eur: Decimal,
        detail: String,
    },
    ConfigChanged {
        config_sha256: String,
        #[serde(default)]
        git_commit: Option<String>,
    },
    /// Confronto tra ledger ed estratto del broker.
    Reconciliation {
        ok: bool,
        detail: String,
    },
}

impl Event {
    pub fn kind(&self) -> &'static str {
        match self {
            Event::Deposit { .. } => "Deposit",
            Event::Withdrawal { .. } => "Withdrawal",
            Event::Fill { .. } => "Fill",
            Event::Dividend { .. } => "Dividend",
            Event::TaxWithheld { .. } => "TaxWithheld",
            Event::StampDuty { .. } => "StampDuty",
            Event::Interest { .. } => "Interest",
            Event::RiskStateChanged { .. } => "RiskStateChanged",
            Event::ConfigChanged { .. } => "ConfigChanged",
            Event::Reconciliation { .. } => "Reconciliation",
        }
    }
}

/// Dati forniti da chi registra un evento. `seq` e hash li calcola il ledger.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct NewEvent {
    pub event_id: String,
    /// Data dell'operazione (quella che fa fede per l'anno fiscale).
    pub date: NaiveDate,
    pub occurred_at: DateTime<Utc>,
    pub recorded_at: DateTime<Utc>,
    pub event: Event,
}

/// Record registrato. L'ordine dei campi è parte del formato dell'hash: non cambiarlo.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Record {
    pub account: String,
    pub seq: u64,
    pub event_id: String,
    pub date: NaiveDate,
    pub occurred_at: DateTime<Utc>,
    pub recorded_at: DateTime<Utc>,
    pub event: Event,
    pub prev_hash: String,
    pub hash: String,
}

/// Corpo del record su cui si calcola l'hash (tutto tranne `hash`).
#[derive(Serialize)]
struct HashedBody<'a> {
    account: &'a str,
    seq: u64,
    event_id: &'a str,
    date: NaiveDate,
    occurred_at: DateTime<Utc>,
    recorded_at: DateTime<Utc>,
    event: &'a Event,
    prev_hash: &'a str,
}

impl Record {
    pub fn compute_hash(&self) -> String {
        let body = HashedBody {
            account: &self.account,
            seq: self.seq,
            event_id: &self.event_id,
            date: self.date,
            occurred_at: self.occurred_at,
            recorded_at: self.recorded_at,
            event: &self.event,
            prev_hash: &self.prev_hash,
        };
        let json = serde_json::to_vec(&body).expect("la serializzazione di un record non fallisce");
        let mut h = Sha256::new();
        h.update(self.prev_hash.as_bytes());
        h.update(&json);
        hex::encode(h.finalize())
    }
}

#[derive(Debug, Error, PartialEq)]
pub enum LedgerError {
    #[error("catena rotta al record seq={seq}: {reason}")]
    BrokenChain { seq: u64, reason: String },
    #[error("evento rifiutato: {0}")]
    Rejected(#[from] ProjectionError),
    #[error("input non valido: {0}")]
    Input(String),
}

/// Verifica la catena di un conto: sequenza continua da 1, hash collegati e corretti.
pub fn verify_chain(records: &[Record]) -> Result<(), LedgerError> {
    let mut prev = GENESIS_HASH.to_string();
    let account = records.first().map(|r| r.account.as_str());
    for (i, r) in records.iter().enumerate() {
        let broken = |reason: String| LedgerError::BrokenChain { seq: r.seq, reason };
        if Some(r.account.as_str()) != account {
            return Err(broken("conto diverso nella stessa catena".into()));
        }
        if r.seq != i as u64 + 1 {
            return Err(broken(format!("seq attesa {}", i + 1)));
        }
        if r.prev_hash != prev {
            return Err(broken(
                "prev_hash non corrisponde all'hash precedente".into(),
            ));
        }
        if r.compute_hash() != r.hash {
            return Err(broken(
                "hash non corrisponde al contenuto (record modificato)".into(),
            ));
        }
        prev = r.hash.clone();
    }
    Ok(())
}

/// Ledger in memoria di un conto. Ogni append è validato contro la proiezione del portafoglio,
/// così il ledger non può mai contenere uno stato impossibile (es. vendere ciò che non si ha).
#[derive(Debug, Clone)]
pub struct Ledger {
    account: String,
    records: Vec<Record>,
    portfolio: Portfolio,
}

impl Ledger {
    pub fn new(account: impl Into<String>) -> Self {
        Self {
            account: account.into(),
            records: Vec::new(),
            portfolio: Portfolio::default(),
        }
    }

    /// Ricostruisce un ledger da record salvati, verificando catena e coerenza.
    pub fn from_records(
        account: impl Into<String>,
        records: Vec<Record>,
    ) -> Result<Self, LedgerError> {
        let account = account.into();
        if records.iter().any(|r| r.account != account) {
            return Err(LedgerError::Input(format!(
                "record di un conto diverso da {account}"
            )));
        }
        verify_chain(&records)?;
        let mut portfolio = Portfolio::default();
        for r in &records {
            portfolio
                .apply(&r.event)
                .map_err(|e| LedgerError::BrokenChain {
                    seq: r.seq,
                    reason: format!("evento incoerente: {e}"),
                })?;
        }
        Ok(Self {
            account,
            records,
            portfolio,
        })
    }

    pub fn account(&self) -> &str {
        &self.account
    }

    pub fn records(&self) -> &[Record] {
        &self.records
    }

    pub fn portfolio(&self) -> &Portfolio {
        &self.portfolio
    }

    pub fn head_hash(&self) -> &str {
        self.records
            .last()
            .map_or(GENESIS_HASH, |r| r.hash.as_str())
    }

    /// Aggiunge un evento. Se l'evento è incoerente col portafoglio, il ledger resta invariato.
    pub fn append(&mut self, e: NewEvent) -> Result<&Record, LedgerError> {
        if e.event_id.trim().is_empty() {
            return Err(LedgerError::Input("event_id vuoto".into()));
        }
        if let Some(last) = self.records.last() {
            if e.date < last.date {
                return Err(LedgerError::Input(format!(
                    "data {} precedente all'ultimo evento ({}): il ledger è in ordine cronologico",
                    e.date, last.date
                )));
            }
        }
        if let Event::Fill {
            settlement_date,
            white_list_pct,
            ..
        } = &e.event
        {
            if settlement_date.is_some_and(|sd| sd < e.date) {
                return Err(LedgerError::Input(
                    "settlement_date precedente alla data dell'operazione".into(),
                ));
            }
            if white_list_pct.is_some_and(|p| p < Decimal::ZERO || p > Decimal::ONE_HUNDRED) {
                return Err(LedgerError::Input(
                    "white_list_pct deve stare in [0, 100]".into(),
                ));
            }
        }
        let mut next = self.portfolio.clone();
        next.apply(&e.event)?;

        let mut r = Record {
            account: self.account.clone(),
            seq: self.records.len() as u64 + 1,
            event_id: e.event_id,
            date: e.date,
            occurred_at: e.occurred_at,
            recorded_at: e.recorded_at,
            event: e.event,
            prev_hash: self.head_hash().to_string(),
            hash: String::new(),
        };
        r.hash = r.compute_hash();
        self.portfolio = next;
        self.records.push(r);
        Ok(self.records.last().expect("appena inserito"))
    }
}
