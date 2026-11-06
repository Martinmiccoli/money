# 09 — Tobin tax (FTT italiana)
- **Ultima verifica:** 2026-11-07 · **Codice:** `config/brokers/trade_republic.toml` (`ftt_it_bps = 20`), `Event::Fill.transaction_tax_eur`
- **Fonte:** L. 228/2012 art. 1 c. 491 e seguenti, modificata dalla L. 199/2025 c. 29. [ecnews, 09/01/2026](https://www.ecnews.it/fiscale/fisco-e-patrimonio/imposte-indirette/legge-di-bilancio-2026-raddoppio-delle-aliquote-di-applicazione-della-tobin-tax/) · [Teleborsa, 02/11/2026](https://www.teleborsa.it/News/2026/11/02/ref-117.html) · [CMS](https://cms.law/en/fra/legal-updates/tax-connect-flash-italy-financial-transaction-tax)

**Si applica:** agli acquisti di azioni di società italiane con capitalizzazione media di novembre **≥ 500 M€**. Gli ETF/OICR sono esclusi (confermato solo da fonti secondarie).

**Aliquote dal 2026:**
- **0,2%** su mercati regolamentati e MTF;
- **0,4%** OTC;
- 0,04% per l'HFT.

**Non deducibile** ai fini delle imposte sui redditi, quindi non entra nel costo fiscale. ✅ nella sostanza, ma il comma esatto non è verificato.

⚠️ **DDL Bilancio 2027, art. 15 (non ancora legge):** raddoppio a **0,4%** in borsa e 0,8% OTC. Se approvato, aggiornare `ftt_it_bps` a 40.

**Nel progetto:** le azioni italiane sono escluse dal live iniziale.
