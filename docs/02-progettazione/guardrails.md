# Guardrails

Regole **non negoziabili**. Sono applicate dal crate Rust `money-core` (`engine/crates/money-core/src/guardrails.rs`) e configurate in `config/guardrails.toml`.

All'avvio la configurazione viene validata: un valore fuori dai limiti consentiti blocca il motore. Allentare un guardrail richiede una modifica al file, un commit con la motivazione e un riavvio. Nessuna strategia, script o LLM può farlo a runtime.

## Capitale e perdite
| ID | Regola | Valore di default | Effetto |
|---|---|---|---|
| G-01 | **Soft stop:** drawdown dal massimo storico dell'equity | -15% | Stato `Sospeso`: nessun nuovo acquisto; restano attivi solo gli stop-loss già piazzati. Per ripartire serve un comando esplicito dell'utente, registrato nel ledger |
| G-02 | **Kill switch duro:** equity rispetto al capitale netto versato | -50% | Stato `Bloccato`: nessun ordine. Si sblocca solo modificando la config e facendo un commit motivato |
| G-03 | Niente leva, short, margin, opzioni, CFD, futures | sempre | Ordine rifiutato |
| G-04 | Cassa mai negativa; si compra solo con la liquidità disponibile | sempre | Ordine rifiutato |

## Ordini
| ID | Regola | Default | Motivo |
|---|---|---|---|
| G-05 | Costo totale dell'ordine (commissione + spread stimato + tasse di transazione) in rapporto al controvalore | ≤ 2% | Con 50 € le commissioni sono il nemico n.1 (Fase 1) |
| G-06 | Rendimento atteso del segnale ≥ k × costo round-trip | k = 2 | Si scambia solo se c'è margine sui costi |
| G-07 | Numero massimo di ordini | 3 al giorno, 10 a settimana | Evita l'overtrading |
| G-08 | Peso massimo di una posizione: singola azione / ETF ampio / ETP crypto (totale) | 20% / 100% / 15% | Concentrazione e volatilità |
| G-09 | Ogni proposta hybrid ha un **prezzo limite** e una **scadenza** | slippage max 1,5%, TTL 72 h | Il tap ritardato non deve rincorrere il prezzo |

> **Conseguenza onesta di G-05 con 50 €:** su Trade Republic un ordine tattico da 1 € di commissione deve valere almeno 50 €. All'inizio quindi il live passerà quasi tutto dal **piano di accumulo** (0 € di commissioni). Gli ordini tattici si sbloccano man mano che il capitale cresce. Il paper trading simula invece il capitale target, per validare la strategia.

## Dati e strumenti
| ID | Regola | Default |
|---|---|---|
| G-10 | Dato più vecchio della soglia oppure job fallito → nessun ordine e alert | 36 h per i dati giornalieri |
| G-11 | **Anti look-ahead:** nei backtest si usano solo dati con `published_at` ≤ data della decisione | sempre |
| G-13 | Solo strumenti in whitelist per modalità. **Live:** azioni USA, ETF UCITS, ETP crypto. **Solo paper:** crypto spot, ETF USA | sempre |

> Nota su G-13: per la normativa UE (PRIIPs/KID) un retail europeo in genere **non può comprare ETF domiciliati negli USA**. Nel live si usano gli equivalenti UCITS.

## Processo
| ID | Regola |
|---|---|
| G-12 | **Registro degli esperimenti:** ogni backtest viene registrato (parametri, periodo, risultati). Il numero di tentativi entra nel Deflated Sharpe Ratio |
| G-14 | Segreti (chiavi API, token) mai nel repo; scansione automatica in CI |
| G-15 | I **soldi veri** (`mode = "hybrid"` o `"live"`) si attivano solo se esiste un report di validazione superato (vedi [validazione](validazione.md)), referenziato per hash |
| G-16 | Ledger append-only: nessun evento viene cancellato o modificato, le correzioni sono nuovi eventi |
| G-17 | Gli LLM (Claude incluso) non piazzano ordini e non modificano i guardrails: producono solo segnali o spiegazioni che passano dal motore |
