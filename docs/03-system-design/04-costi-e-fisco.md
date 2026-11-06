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

### Regole implementate (M2, verificate il 2026-11-07)
Le schede con fonti sono in [`knowledge/fisco/`](../../knowledge/fisco/README.md), i parametri in `config/fisco.toml`.
1. **Costo fiscale:** costo medio ponderato per titolo, commissioni d'acquisto incluse e commissioni di vendita dedotte dal ricavo (art. 6 D.Lgs. 461/97 → art. 306 nuovo TUIR).
2. **Zainetto:** le minusvalenze sono registrate per anno di origine e **scadono il 31/12 dell'anno N+4**. Si consumano partendo dalle più vecchie. Una perdita compensa **solo plusvalenze successive**: in amministrato non c'è rimborso delle imposte già pagate nell'anno.
3. **ETF:** la plusvalenza è RC al 26% e non è compensabile. La minusvalenza è RD e va nello zainetto. Per gli ETF con titoli di Stato *white list*, sia il guadagno sia la perdita contano per `(1 − p) + p × 48,08%`.
4. **Anno fiscale:** vale la **data di regolamento** (T+2), come indica l'AdE per gli OICR; per prudenza la usiamo per tutto. Una vendita del 30/12 finisce nell'anno successivo.
5. **Dividendi USA:** ritenuta del 15% (Trade Republic è un Qualified Intermediary), poi il 26% sul netto (circa 37,1% in totale).
6. **Bollo:** 0,2% annuo pro rata, pagato dall'intermediario. Il motore lo stima e lo riconcilia. 🟡 C'è un possibile minimo di 1 € da verificare.
7. **Tobin tax:** 0,2% sugli acquisti in borsa di azioni italiane con capitalizzazione ≥ 500 M€. **Non deducibile**, quindi non entra nel costo. ⚠️ Il DDL Bilancio 2027 propone di raddoppiarla.
8. **Crypto spot (solo paper):** 33% dal 2026, con uno zainetto separato.

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
