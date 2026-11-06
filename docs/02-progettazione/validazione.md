# Piano di validazione

Obiettivo: decidere **con i numeri** se una strategia merita soldi veri, senza ingannarsi da soli (overfitting, look-ahead, costi ignorati).

## Gate 0 — Ricerca (backtest)
- **Dati:** il massimo storico disponibile (azioni USA dal 2016 con Alpaca; più indietro per ETF e fattori dove possibile).
- **Split:** l'ultimo 20% del periodo resta **hold-out** e si usa **una sola volta**, alla fine.
- **Metodo:** walk-forward più purged/embargoed cross-validation (López de Prado) sul restante 80%.
- **Costi:** modello di Trade Republic con 1 € a ordine (0 € sui piani di accumulo), spread stimato, Tobin tax dove applicabile, cambio EUR/USD. Il modello è lo stesso usato in live (`money-core`).
- **Tasse:** si calcola il rendimento **netto** con il 26% e le regole sulla compensazione delle minusvalenze (gli ETF non compensano).
- **Capitale simulato:** 50 € **e** 1.000 €, per vedere quanto pesano i costi.
- **Benchmark:** ETF UCITS sull'S&P 500 (o MSCI World) comprato e tenuto, al netto degli stessi costi.

**Per passare il Gate 0, sull'hold-out:**
| Metrica | Soglia |
|---|---|
| Sharpe netto (costi + tasse) | > 1,0 |
| Max drawdown | < 15% |
| Rendimento netto vs benchmark | > 0 |
| Deflated Sharpe Ratio (calcolato sul numero di tentativi del registro G-12) | probabilità > 95% |
| Probability of Backtest Overfitting (PBO) | < 0,5 |
| Numero di trade | ≥ 30 (altrimenti la statistica è inaffidabile) |

## Gate 1 — Paper trading
- **Durata:** almeno 3 mesi e almeno 20 trade; si prolunga fino a 6 mesi se i trade sono pochi.
- **Esecuzione:** SimBroker più Alpaca Paper, in automatico.
- **Si confronta il paper con il backtest dello stesso periodo:** se il paper rende molto meno (es. Sharpe sotto il 50% di quello previsto), qualcosa nel modello è sbagliato e si torna alla ricerca.
- **Per passare il Gate 1 servono:**
  - Sharpe > 1;
  - drawdown < 15%;
  - rendimento migliore del benchmark nello stesso periodo;
  - nessuna violazione dei guardrails non spiegata.

## Gate 2 — Live
- Report di validazione generato automaticamente (`reports/validation/<data>.md` + hash), approvato dall'utente.
- `mode = "live"` in `config/guardrails.toml`, con commit che referenzia l'hash del report (G-15).
- **Si parte con 50 €**. I versamenti aggiuntivi arrivano solo dopo 3 mesi di live coerenti con il paper.
- Monitoraggio continuo: se il live viola le soglie del Gate 1 per 2 mesi, si torna in paper.

## Cosa NON conta come validazione
- Un singolo mese positivo.
- Un backtest senza costi, senza tasse o con un hold-out già "guardato".
- Il miglior risultato tra 100 combinazioni di parametri, senza la correzione Deflated Sharpe.
