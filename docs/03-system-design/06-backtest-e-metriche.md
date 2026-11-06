# 3.6 — Backtest e metriche

## Due motori di backtest, ruoli diversi
| | Ricerca rapida | Validazione (Gate 0) |
|---|---|---|
| Strumento | vectorbt (Python, vettoriale) | simulatore event-driven giornaliero (Python) che chiama `money-core` via PyO3 |
| Scopo | esplorare le idee, sweep di parametri | il numero che decide se si va avanti |
| Costi, tasse, guardrails | approssimati | **identici al live** |
| Registro G-12 | sì (ogni sweep conta come N tentativi) | sì |

## Loop del simulatore (per ogni giorno di borsa t)
1. Si caricano solo i dati con `available_at < apertura(t)` (G-11): un layer di accesso dati lo impone, la strategia non può bypassarlo.
2. Si calcolano i segnali e i pesi target (stesso codice di produzione).
3. Si generano gli ordini, li si passa a `money-core::guardrails::check_order` e si registrano i rifiuti.
4. Fill al prezzo di apertura di t più costi (`money-core::costs`).
5. Eventi nel ledger simulato: `money-core::tax` aggiorna lo zainetto e le tasse al realizzo.
6. `money-core::risk::RiskMachine.update(equity)`. Se il conto è sospeso, nel backtest si assume la ripartenza dopo 20 giorni (scenario conservativo, parametrizzabile).

## Bias e come li neutralizziamo
| Bias | Contromisura |
|---|---|
| Look-ahead | `available_at` obbligatorio e layer dati point-in-time |
| Survivorship | universi point-in-time; prezzi dei delistati (problema aperto, [3.1](01-segnali.md)) |
| Selezione col senno di poi | lista dei superinvestor selezionata point-in-time (S2) |
| Overfitting | registro G-12, DSR, PBO, hold-out bloccato |
| Costi ignorati | modello di costi unico, con sensitivity a ×2 |
| Data snooping sul benchmark | il benchmark è fissato a priori (ETF UCITS globale con piano di accumulo) |

## Metriche (tutte al netto di costi e tasse, in EUR)
| Metrica | Definizione |
|---|---|
| CAGR | `(V_fine / V_inizio)^(252/N) − 1`, al netto dei flussi (time-weighted) |
| Volatilità | `std(r_giorno) · √252` |
| Sharpe | `(mean(r − rf) / std(r − rf)) · √252`, con rf = €STR (BCE) |
| Sortino, Max drawdown, Calmar | standard |
| Turnover, cost drag, tax drag | annui, in % dell'equity |
| Alpha / Information ratio | rispetto al benchmark |
| **Deflated Sharpe Ratio** | Bailey & López de Prado (2014): probabilità che lo Sharpe vero sia > 0 tenendo conto di N tentativi (dal registro), asimmetria, curtosi e lunghezza del campione |
| **PBO** | Bailey, Borwein, López de Prado, Zhu (2017), CSCV con S = 16 blocchi: frequenza con cui la configurazione migliore in-sample finisce sotto la mediana out-of-sample |

## Registro esperimenti (G-12)
- **Ogni** esecuzione del simulatore o di uno sweep scrive automaticamente in `research.experiment`: versione del codice, config, periodo, metriche e famiglia di tentativi.
- Il DSR di una strategia usa il **numero totale di tentativi della sua famiglia**.
- **Hold-out:** l'accesso richiede un flag esplicito e viene registrato in `research.holdout_access`. Dal secondo accesso il report è marcato "hold-out contaminato" e non può superare il Gate 0.

## Report di validazione
Viene generato automaticamente in `reports/validation/AAAA-MM-GG-<strategia>.md` e contiene:
- metriche;
- curve contro il benchmark;
- sensibilità ai costi (×1, ×2);
- breakdown per anno;
- DSR e PBO;
- elenco dei tentativi.

Il suo sha256 è quello richiesto da G-15 per passare a `hybrid`/`live`.

## Note dall'implementazione (M3, 2026-11-07)
- **G-10 e il lunedì:** con la soglia di 36 h, alle 9:00 del lunedì il dato più recente (venerdì, disponibile alle 23:00) ha circa 58 h, quindi ogni ordine del lunedì e del giorno dopo un festivo USA viene rifiutato. Nel backtest l'ordine si riprova il giorno dopo. **Da decidere prima del paper trading (M6):** misurare l'età in ore di borsa oppure accettarlo così. Cambiare la misura equivale a toccare un guardrail, quindi serve una richiesta esplicita dell'utente.
- **Prezzi dei proxy:** si usano le serie USA rettificate (dividendi reinvestiti, come un ETF ad accumulo), convertite in EUR e ridotte di un costo annuo stimato (`proxy_drag_bps_per_year` in `config/validation.toml`).
- **Tasse latenti:** il CAGR netto include la liquidazione finale (vendita di tutto, con commissione e 26%). Così una strategia che realizza spesso e una che tiene fermo si confrontano alla pari.
