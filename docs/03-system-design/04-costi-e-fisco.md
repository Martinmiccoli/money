# 3.4 — Modello dei costi e motore fiscale

Entrambi stanno in `money-core` e sono **gli stessi** in backtest, paper e live (principio 2 dell'architettura).

## Modello dei costi
Profilo per broker in `config/brokers/<nome>.toml`:
```toml
[trade_republic]
fee_per_order_eur = 1.0
fee_savings_plan_eur = 0.0
spread_bps = { etf_ucits = 10, stock_us = 20, crypto_etp = 40 }   # ⚠️ STIME: calibrare sui fill reali
fx_embedded = true            # le azioni USA si scambiano in EUR (sede LS Exchange): il cambio è nello spread
ftt_it_bps = 20               # Tobin tax sugli acquisti di azioni italiane con cap ≥ 500 M€ (escluse dal live)
```
Costo di un lato = `commissione + controvalore × spread/2 + FTT` (FTT solo sugli acquisti).

**Calibrazione:** ogni `Fill` reale registra il prezzo ottenuto e il prezzo di riferimento. Lo spread stimato si aggiorna con la mediana degli ultimi N fill. In paper si usa il profilo Trade Republic anche quando il fill avviene su Alpaca.

## Motore fiscale (regime amministrato, persona fisica residente)
> Regole da [broker-e-fisco.md](../01-raccolta/broker-e-fisco.md). Ognuna verrà trascritta in `knowledge/fisco/` con fonte e data di verifica. ⚠️ indica un punto da verificare prima dell'implementazione.

| Categoria fiscale | Strumenti | Plusvalenze | Minusvalenze |
|---|---|---|---|
| **Redditi diversi (RD)** | azioni, ETC/ETN, **ETP crypto** ⚠️ (in genere strutturati come ETN), certificati | tassate al 26%, **compensabili** con lo zainetto | vanno nello zainetto RD |
| **Redditi di capitale (RC)** | **plusvalenze da ETF/OICR**, dividendi, cedole | tassate al 26% **senza compensazione** | (le minusvalenze da ETF sono RD → zainetto) |
| Crypto spot (solo paper) | — | 33% | paniere separato |

### Regole implementate
1. **Costo fiscale:** costo medio ponderato per titolo (art. 68 c. 6 TUIR) ⚠️ verificare l'applicazione in amministrato su Trade Republic.
2. **Zainetto:** le minusvalenze RD vengono registrate per anno di origine e **scadono il 31/12 dell'anno N+4**. Si consumano FIFO, cioè prima le più vecchie.
3. **ETF:** la plusvalenza è RC al 26% e non può essere compensata. La minusvalenza va nello zainetto RD.
4. **Dividendi USA:** ritenuta del 15% con W-8BEN, poi il 26% sul netto (circa 37,1% in totale). ⚠️ verificare che Trade Republic gestisca il W-8BEN.
5. **Bollo:** 0,2% annuo pro rata sul valore del dossier, pagato dall'intermediario. Il motore lo stima e lo riconcilia.
6. **Tobin tax:** 0,2% sugli acquisti di azioni italiane con capitalizzazione ≥ 500 M€ (escluse dal live iniziale). ETF esclusi.

### Decisioni fiscalmente consapevoli
- A parità di segnale, il motore **preferisce realizzare minusvalenze in scadenza** (compensazione con plusvalenze RD) e segnala lo zainetto che sta per scadere.
- **Asimmetria degli ETF:** per i satellite tattici con alto turnover si preferiscono, a parità di esposizione, strumenti RD (ETC/ETN) quando esistono, perché le loro plusvalenze sono compensabili. La regola va validata in backtest: non deve peggiorare il rischio.
- Tutte le metriche di validazione sono **al netto delle tasse**, calcolate al realizzo.

## Report dell'agente fiscale
`money-core::tax::report(anno)` produce un report **deterministico**:
- plusvalenze e minusvalenze per categoria;
- zainetto per anno di scadenza;
- tasse stimate e tasse trattenute dal broker (eventi `TaxWithheld`), con le differenze;
- bollo e dividendi.

Claude (ADR-004) lo legge, lo spiega e segnala le differenze. In regime dichiarativo prepara la bozza dei quadri RT/RW. Ogni report porta l'avviso di verifica da parte di un commercialista.
