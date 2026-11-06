//! Binding Python di `money-core` (ADR-001): il backtest usa **lo stesso** codice
//! di costi, ledger e fisco del paper e del live.
//!
//! Il confine è volutamente semplice: gli oggetti attraversano il confine come JSON,
//! e gli importi sono stringhe decimali (in Python: `decimal.Decimal(s)`), mai float.

use std::collections::BTreeMap;

use chrono::NaiveDate;

use money_core::{
    config::GuardrailsConfig as CoreGuardrails,
    costs::{BrokerProfile as CoreBroker, OrderKind},
    guardrails,
    ledger::{self, Ledger as CoreLedger, NewEvent, Record},
    risk::{RiskMachine as CoreRisk, RiskState},
    tax::{self, TaxCategory, TaxRules as CoreRules},
    types::{AssetClass, OrderRequest, PortfolioSnapshot, Side},
};
use pyo3::{exceptions::PyValueError, prelude::*};
use rust_decimal::Decimal;
use serde::de::DeserializeOwned;

fn err(e: impl std::fmt::Display) -> PyErr {
    PyValueError::new_err(e.to_string())
}

fn from_json<T: DeserializeOwned>(s: &str, what: &str) -> PyResult<T> {
    serde_json::from_str(s).map_err(|e| err(format!("{what}: JSON non valido: {e}")))
}

fn to_json<T: serde::Serialize>(v: &T) -> String {
    serde_json::to_string(v).expect("la serializzazione non fallisce")
}

/// Converte una stringa in un enum serde (es. "etf_ucits" -> AssetClass::EtfUcits).
fn enum_from_str<T: DeserializeOwned>(s: &str, what: &str) -> PyResult<T> {
    serde_json::from_value(serde_json::Value::String(s.to_string()))
        .map_err(|_| err(format!("{what} non valido: {s}")))
}

fn dec(s: &str, what: &str) -> PyResult<Decimal> {
    s.parse()
        .map_err(|_| err(format!("{what} non è un decimale valido: {s}")))
}

/// Ledger in memoria di un conto, con validazione di ogni evento.
#[pyclass(module = "money_py")]
struct Ledger {
    inner: CoreLedger,
}

#[pymethods]
impl Ledger {
    #[new]
    fn new(account: &str) -> Self {
        Self {
            inner: CoreLedger::new(account),
        }
    }

    /// Ricostruisce un ledger da record salvati (JSON array), verificando la catena.
    #[staticmethod]
    fn from_records(account: &str, records_json: &str) -> PyResult<Self> {
        let records: Vec<Record> = from_json(records_json, "records")?;
        Ok(Self {
            inner: CoreLedger::from_records(account, records).map_err(err)?,
        })
    }

    /// Aggiunge un evento (JSON di `NewEvent`) e restituisce il record registrato (JSON).
    fn append(&mut self, new_event_json: &str) -> PyResult<String> {
        let e: NewEvent = from_json(new_event_json, "new_event")?;
        self.inner.append(e).map(to_json).map_err(err)
    }

    fn records_json(&self) -> String {
        to_json(&self.inner.records())
    }

    fn portfolio_json(&self) -> String {
        to_json(self.inner.portfolio())
    }

    fn head_hash(&self) -> String {
        self.inner.head_hash().to_string()
    }

    fn account(&self) -> String {
        self.inner.account().to_string()
    }

    fn __len__(&self) -> usize {
        self.inner.records().len()
    }
}

/// Verifica la catena di hash di un conto. Solleva ValueError se è rotta.
#[pyfunction]
fn verify_chain(records_json: &str) -> PyResult<()> {
    let records: Vec<Record> = from_json(records_json, "records")?;
    ledger::verify_chain(&records).map_err(err)
}

/// Hash di un record (per controlli incrociati con il database).
#[pyfunction]
fn record_hash(record_json: &str) -> PyResult<String> {
    let r: Record = from_json(record_json, "record")?;
    Ok(r.compute_hash())
}

/// Profilo costi di un broker (`config/brokers/*.toml`).
#[pyclass(module = "money_py")]
struct BrokerProfile {
    inner: CoreBroker,
}

#[pymethods]
impl BrokerProfile {
    #[staticmethod]
    fn load(path: &str) -> PyResult<Self> {
        Ok(Self {
            inner: CoreBroker::load(path).map_err(err)?,
        })
    }

    #[staticmethod]
    fn from_toml(s: &str) -> PyResult<Self> {
        Ok(Self {
            inner: CoreBroker::from_toml_str(s).map_err(err)?,
        })
    }

    /// Costi di un lato. Importi come stringhe decimali; restituisce il JSON di `Quote`.
    #[pyo3(signature = (asset_class, side, qty, ref_price_eur, kind = "regular", ftt_liable = false))]
    fn quote(
        &self,
        asset_class: &str,
        side: &str,
        qty: &str,
        ref_price_eur: &str,
        kind: &str,
        ftt_liable: bool,
    ) -> PyResult<String> {
        let q = self
            .inner
            .quote(
                enum_from_str::<AssetClass>(asset_class, "asset_class")?,
                enum_from_str::<Side>(side, "side")?,
                enum_from_str::<OrderKind>(kind, "kind")?,
                dec(qty, "qty")?,
                dec(ref_price_eur, "ref_price_eur")?,
                ftt_liable,
            )
            .map_err(err)?;
        Ok(to_json(&q))
    }

    /// Costo stimato di un lato per un controvalore in EUR (stringa decimale).
    #[pyo3(signature = (asset_class, side, notional_eur, kind = "regular", ftt_liable = false))]
    fn est_side_cost_eur(
        &self,
        asset_class: &str,
        side: &str,
        notional_eur: &str,
        kind: &str,
        ftt_liable: bool,
    ) -> PyResult<String> {
        let c = self
            .inner
            .est_side_cost_eur(
                enum_from_str::<AssetClass>(asset_class, "asset_class")?,
                enum_from_str::<Side>(side, "side")?,
                enum_from_str::<OrderKind>(kind, "kind")?,
                dec(notional_eur, "notional_eur")?,
                ftt_liable,
            )
            .map_err(err)?;
        Ok(c.to_string())
    }
}

/// Regole fiscali (`config/fisco.toml`).
#[pyclass(module = "money_py")]
struct TaxRules {
    inner: CoreRules,
}

#[pymethods]
impl TaxRules {
    #[staticmethod]
    fn load(path: &str) -> PyResult<Self> {
        Ok(Self {
            inner: CoreRules::load(path).map_err(err)?,
        })
    }

    #[staticmethod]
    fn from_toml(s: &str) -> PyResult<Self> {
        Ok(Self {
            inner: CoreRules::from_toml_str(s).map_err(err)?,
        })
    }
}

fn instruments(json: &str) -> PyResult<BTreeMap<String, TaxCategory>> {
    from_json(json, "instruments (mappa strumento -> RD|RC|CRYPTO)")
}

/// Report fiscale annuale (JSON di `TaxReport`).
#[pyfunction]
fn tax_report(
    records_json: &str,
    instruments_json: &str,
    rules: &TaxRules,
    year: i32,
) -> PyResult<String> {
    let records: Vec<Record> = from_json(records_json, "records")?;
    tax::report(
        &records,
        &rules.inner,
        &instruments(instruments_json)?,
        year,
    )
    .map(|r| to_json(&r))
    .map_err(err)
}

/// Imposta che il broker tratterrebbe sull'ultimo record (stringa decimale).
#[pyfunction]
fn tax_due_for_last(
    records_json: &str,
    instruments_json: &str,
    rules: &TaxRules,
) -> PyResult<String> {
    let records: Vec<Record> = from_json(records_json, "records")?;
    tax::tax_due_for_last(&records, &rules.inner, &instruments(instruments_json)?)
        .map(|d| d.to_string())
        .map_err(err)
}

/// Stima del bollo da una lista JSON di coppie ["AAAA-MM-GG", "valore"].
#[pyfunction]
fn stamp_duty_estimate(rules: &TaxRules, daily_values_json: &str) -> PyResult<String> {
    let v: Vec<(NaiveDate, Decimal)> = from_json(daily_values_json, "daily_values")?;
    Ok(tax::stamp_duty_estimate(&rules.inner, &v).to_string())
}

/// Configurazione dei guardrails (`config/guardrails.toml`), validata al caricamento.
#[pyclass(module = "money_py")]
struct GuardrailsConfig {
    inner: CoreGuardrails,
}

#[pymethods]
impl GuardrailsConfig {
    #[staticmethod]
    fn load(path: &str) -> PyResult<Self> {
        Ok(Self {
            inner: CoreGuardrails::load(path).map_err(err)?,
        })
    }

    #[staticmethod]
    fn from_toml(s: &str) -> PyResult<Self> {
        Ok(Self {
            inner: CoreGuardrails::from_toml_str(s).map_err(err)?,
        })
    }

    fn mode(&self) -> String {
        format!("{:?}", self.inner.mode).to_lowercase()
    }
}

/// Controllo pre-trade. Restituisce la lista JSON delle violazioni (vuota = ordine ammesso):
/// `[{"code": "G-05", "detail": "..."}]`.
#[pyfunction]
fn check_order(
    cfg: &GuardrailsConfig,
    risk_state: &str,
    portfolio_json: &str,
    order_json: &str,
) -> PyResult<String> {
    let state: RiskState = enum_from_str(risk_state, "risk_state (Active|Suspended|Locked)")?;
    let pf: PortfolioSnapshot = from_json(portfolio_json, "portfolio")?;
    let o: OrderRequest = from_json(order_json, "order")?;
    let violations = match guardrails::check_order(&cfg.inner, state, &pf, &o) {
        Ok(()) => Vec::new(),
        Err(v) => v
            .iter()
            .map(|x| serde_json::json!({"code": x.code(), "detail": format!("{x:?}")}))
            .collect(),
    };
    Ok(to_json(&violations))
}

/// Macchina a stati del rischio (G-01 soft stop, G-02 kill switch).
#[pyclass(module = "money_py")]
struct RiskMachine {
    inner: CoreRisk,
}

#[pymethods]
impl RiskMachine {
    #[new]
    fn new(initial_equity_eur: f64) -> Self {
        Self {
            inner: CoreRisk::new(initial_equity_eur),
        }
    }

    /// "Active" | "Suspended" | "Locked".
    fn state(&self) -> String {
        format!("{:?}", self.inner.state())
    }

    fn high_water_mark_eur(&self) -> f64 {
        self.inner.high_water_mark_eur()
    }

    /// Aggiorna con l'equity corrente; restituisce l'evento JSON della transizione o None.
    fn update(&mut self, cfg: &GuardrailsConfig, equity_eur: f64) -> Option<String> {
        self.inner
            .update(&cfg.inner, equity_eur)
            .map(|e| to_json(&e))
    }

    /// Ripartenza esplicita dopo un soft stop.
    fn resume(&mut self, equity_eur: f64) -> PyResult<String> {
        self.inner
            .resume(equity_eur)
            .map(|e| to_json(&e))
            .map_err(|e| err(format!("{e:?}")))
    }
}

#[pymodule]
fn _core(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Ledger>()?;
    m.add_class::<BrokerProfile>()?;
    m.add_class::<TaxRules>()?;
    m.add_class::<GuardrailsConfig>()?;
    m.add_class::<RiskMachine>()?;
    m.add_function(wrap_pyfunction!(check_order, m)?)?;
    m.add_function(wrap_pyfunction!(verify_chain, m)?)?;
    m.add_function(wrap_pyfunction!(record_hash, m)?)?;
    m.add_function(wrap_pyfunction!(tax_report, m)?)?;
    m.add_function(wrap_pyfunction!(tax_due_for_last, m)?)?;
    m.add_function(wrap_pyfunction!(stamp_duty_estimate, m)?)?;
    m.add("GENESIS_HASH", ledger::GENESIS_HASH)?;
    m.add("TAX_DISCLAIMER", tax::DISCLAIMER)?;
    Ok(())
}
