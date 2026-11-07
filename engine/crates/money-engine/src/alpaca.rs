//! Alpaca **Paper**: copia "ombra" degli ordini, solo per confrontare il fill simulato con uno reale.
//! Il ledger usa sempre il fill del SimBroker con i costi di Trade Republic.

use anyhow::{bail, Context, Result};
use serde::Deserialize;

/// G-17: l'unico endpoint ammesso è quello paper. Nessun altro URL è configurabile.
pub const PAPER_URL: &str = "https://paper-api.alpaca.markets";

pub struct AlpacaPaper {
    client: reqwest::blocking::Client,
    key: String,
    secret: String,
}

#[derive(Debug, Deserialize)]
pub struct AlpacaOrder {
    pub id: String,
    pub status: String,
    pub filled_avg_price: Option<String>,
    pub filled_at: Option<String>,
}

impl AlpacaPaper {
    pub fn from_env() -> Option<Self> {
        let key = std::env::var("ALPACA_KEY_ID")
            .ok()
            .filter(|s| !s.is_empty())?;
        let secret = std::env::var("ALPACA_SECRET_KEY")
            .ok()
            .filter(|s| !s.is_empty())?;
        Some(Self {
            client: reqwest::blocking::Client::builder()
                .timeout(std::time::Duration::from_secs(30))
                .build()
                .ok()?,
            key,
            secret,
        })
    }

    fn req(&self, m: reqwest::Method, path: &str) -> reqwest::blocking::RequestBuilder {
        debug_assert!(PAPER_URL.contains("paper-api"));
        self.client
            .request(m, format!("{PAPER_URL}{path}"))
            .header("APCA-API-KEY-ID", &self.key)
            .header("APCA-API-SECRET-KEY", &self.secret)
    }

    /// Ordine a mercato per importo in USD (frazioni). `side`: "buy" | "sell".
    pub fn submit_notional(
        &self,
        symbol: &str,
        side: &str,
        notional_usd: f64,
        client_id: &str,
    ) -> Result<AlpacaOrder> {
        let crypto = symbol.contains('/');
        let body = serde_json::json!({
            "symbol": symbol,
            "side": side,
            "type": "market",
            "time_in_force": if crypto { "gtc" } else { "day" },
            "notional": format!("{notional_usd:.2}"),
            "client_order_id": client_id,
        });
        let r = self
            .req(reqwest::Method::POST, "/v2/orders")
            .json(&body)
            .send()?;
        let status = r.status();
        let text = r.text()?;
        if !status.is_success() {
            bail!("Alpaca {status}: {text}");
        }
        serde_json::from_str(&text).context("risposta Alpaca non valida")
    }

    pub fn order(&self, id: &str) -> Result<AlpacaOrder> {
        let r = self
            .req(reqwest::Method::GET, &format!("/v2/orders/{id}"))
            .send()?;
        let status = r.status();
        let text = r.text()?;
        if !status.is_success() {
            bail!("Alpaca {status}: {text}");
        }
        serde_json::from_str(&text).context("risposta Alpaca non valida")
    }
}
