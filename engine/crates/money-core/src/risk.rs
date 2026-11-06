//! Macchina a stati del rischio (G-01 soft stop, G-02 kill switch).
//!
//! Attivo ──(drawdown dal massimo ≥ soft_stop)──▶ Sospeso ──(resume esplicito)──▶ Attivo
//!   │                                              │
//!   └──────(equity ≤ versato × (1 - kill))─────────┴──▶ Bloccato (definitivo)

use crate::config::GuardrailsConfig;

#[derive(Debug, Clone, Copy, PartialEq, Eq, serde::Serialize, serde::Deserialize)]
pub enum RiskState {
    /// Operatività normale.
    Active,
    /// Soft stop: nessun nuovo acquisto, le vendite restano permesse. Serve un resume esplicito.
    Suspended,
    /// Kill switch: nessun ordine. Si sblocca solo modificando la configurazione.
    Locked,
}

#[derive(Debug, Clone)]
pub struct RiskMachine {
    state: RiskState,
    high_water_mark_eur: f64,
}

/// Evento prodotto da una transizione, da scrivere nel ledger.
#[derive(Debug, Clone, PartialEq, serde::Serialize)]
pub enum RiskEvent {
    SoftStopTriggered { equity_eur: f64, drawdown_pct: f64 },
    KillSwitchTriggered { equity_eur: f64, loss_pct: f64 },
    Resumed { new_high_water_mark_eur: f64 },
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ResumeError {
    NotSuspended,
    Locked,
}

impl RiskMachine {
    pub fn new(initial_equity_eur: f64) -> Self {
        Self {
            state: RiskState::Active,
            high_water_mark_eur: initial_equity_eur,
        }
    }

    /// Ricostruisce lo stato a partire dal ledger.
    pub fn restore(state: RiskState, high_water_mark_eur: f64) -> Self {
        Self {
            state,
            high_water_mark_eur,
        }
    }

    pub fn state(&self) -> RiskState {
        self.state
    }

    pub fn high_water_mark_eur(&self) -> f64 {
        self.high_water_mark_eur
    }

    /// Aggiorna lo stato con una nuova valutazione dell'equity.
    pub fn update(&mut self, cfg: &GuardrailsConfig, equity_eur: f64) -> Option<RiskEvent> {
        if self.state == RiskState::Locked {
            return None;
        }

        // Un valore non finito è trattato come la condizione peggiore.
        let equity = if equity_eur.is_finite() {
            equity_eur
        } else {
            0.0
        };

        let deposits = cfg.capital.net_deposits_eur;
        let loss_pct = (1.0 - equity / deposits) * 100.0;
        if loss_pct >= cfg.drawdown.hard_kill_pct {
            self.state = RiskState::Locked;
            return Some(RiskEvent::KillSwitchTriggered {
                equity_eur: equity,
                loss_pct,
            });
        }

        if self.state == RiskState::Active {
            if equity > self.high_water_mark_eur {
                self.high_water_mark_eur = equity;
            }
            let dd_pct = (1.0 - equity / self.high_water_mark_eur) * 100.0;
            if dd_pct >= cfg.drawdown.soft_stop_pct {
                self.state = RiskState::Suspended;
                return Some(RiskEvent::SoftStopTriggered {
                    equity_eur: equity,
                    drawdown_pct: dd_pct,
                });
            }
        }
        None
    }

    /// Ripartenza esplicita dopo un soft stop: l'utente prende atto della perdita e il
    /// massimo storico viene riportato all'equity corrente.
    pub fn resume(&mut self, equity_eur: f64) -> Result<RiskEvent, ResumeError> {
        match self.state {
            RiskState::Locked => Err(ResumeError::Locked),
            RiskState::Active => Err(ResumeError::NotSuspended),
            RiskState::Suspended => {
                self.state = RiskState::Active;
                self.high_water_mark_eur = equity_eur;
                Ok(RiskEvent::Resumed {
                    new_high_water_mark_eur: equity_eur,
                })
            }
        }
    }
}
