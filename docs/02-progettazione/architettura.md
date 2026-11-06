# Fase 2 — Architettura

> Si basa su [requisiti](../00-requisiti.md) e [sintesi della Fase 1](../01-raccolta/00-sintesi.md).
> Decisioni formali: [ADR](adr/). Regole non negoziabili: [guardrails](guardrails.md). Criteri per andare live: [validazione](validazione.md).

## Principi
1. **Le regole stanno nel codice, non nella disciplina.** Ogni limite di rischio è applicato dal motore Rust e nessuna strategia, script o LLM può aggirarlo.
2. **Una sola fonte di verità per costi, tasse e rischio.** Backtest, paper e live usano lo stesso codice (crate Rust `money-core`, esposto a Python via PyO3). Se il backtest usa un modello di costi diverso dal live, il backtest mente.
3. **I numeri li fa il codice, le spiegazioni Claude.** L'agente fiscale e gli LLM non calcolano mai importi: leggono i report deterministici, li spiegano e li controllano.
4. **Tutto è un evento immutabile.** Il ledger è append-only: ogni segnale, ordine, fill, stop e ripartenza resta tracciato.
5. **Lento e robusto, non veloce.** Si opera da una volta al giorno a una al mese, quindi la latenza non conta. Contano correttezza, costi e auditabilità.
6. **Riusare prima di costruire:** SEC EDGAR + edgartools, ccxt, vectorbt, FinBERT, Alpaca paper.

## Vista d'insieme

```
                ┌───────────────────────── Oracle Cloud Always Free (VM ARM) ─────────────────────────┐
                │                                                                                      │
 Fonti esterne  │  ① INGEST (Python, cron)          ② SEGNALI (Python)          ③ COMBINER (Python ML)   │
 ─────────────  │  prezzi, SEC 13F/Form4,     ──▶   un modulo per pilastro ──▶  pesi target del         │
 Alpaca data    │  news/GDELT, macro, crypto        → Signal standard           portafoglio + spiegazione│
 SEC EDGAR      │            │                              │                            │               │
 GDELT/Marketaux│            ▼                              ▼                            ▼               │
 FRED/ECB       │  ┌──────────────────────── PostgreSQL (+Timescale) / Parquet ─────────────────────┐   │
 Binance dumps  │  │ market · signals · portfolio · ledger (append-only) · ops (heartbeat, registro)│   │
                │  └────────────────────────────────────────────────────────────────────────────────┘   │
                │            ▲                              │                                            │
                │            │                              ▼                                            │
                │  ⑥ API + WEBAPP (TypeScript)     ④ MOTORE (Rust)                                       │
                │  dashboard, approvazioni,  ◀──── money-core: GUARDRAILS · rischio · costi · fisco      │
                │  notifiche Telegram/push         money-engine: ordini → adapter di esecuzione          │
                │                                    ├─ SimBroker (paper interno con costi IT)           │
                └──────────────┬─────────────────────├─ AlpacaPaper (paper su broker reale)  ───────────┘
                               │                     ├─ ManualTap (proposta → notifica → tap su TR)
                       Cloudflare Tunnel             └─ [futuro] Saxo / IBKR (automazione totale)
                               │
                        📱 Telefono / browser            ⑤ AGENTE FISCALE = Claude Code
                                                           knowledge/fisco + report deterministici dal ledger
```

## Componenti

### ① Ingest — `research/money_research/ingest/` (Python)
| Fonte | Dati | Frequenza |
|---|---|---|
| Alpaca Market Data (Basic) | barre giornaliere e intraday USA, storico dal 2016 | giornaliera |
| SEC EDGAR + `edgartools` | Form 4 (insider), 13F (superinvestor) | giornaliera / trimestrale |
| Camera e Senato USA (PDF) | trade del Congresso | settimanale |
| GDELT, Marketaux (100 richieste/giorno) | news e tono | giornaliera |
| FRED, ECB, Eurostat | macro e regime | giornaliera |
| data.binance.vision + API pubbliche | crypto (solo paper) | giornaliera |
| Prezzi ETF UCITS / ETP | da definire nella Fase 3 (nessuna fonte gratuita certa) | — |

Ogni job scrive **sempre** la data di riferimento del dato (`as_of`) e quella di pubblicazione (`published_at`). Nei backtest è ammesso solo ciò che era pubblico a quella data (anti look-ahead, vedi G-11).

### ② Segnali — `research/money_research/signals/` (Python)
Contratto unico per ogni pilastro:
```
Signal { instrument, as_of, horizon_days, score ∈ [-1, 1], confidence ∈ [0, 1], pillar, explain }
```
| Pilastro | Modulo | Ruolo (dalle evidenze della Fase 1) |
|---|---|---|
| Insider buying (cluster, opportunistic) | `insider` | segnale primario sulle azioni USA |
| Superinvestor 13F | `superinvestor` | universo e base di qualità |
| Fattori (trend, momentum, low-vol, quality) | `factors` | motore principale su ETF |
| Sentiment (news, GDELT, FinBERT locale) | `sentiment` | filtro anti-hype e rischio |
| Congresso USA (leader) | `congress` | segnale secondario |
| Regime macro e volatilità | `regime` | riduce l'esposizione nei regimi avversi |

### ③ Combiner — `research/money_research/combiner/` (Python)
Trasforma i segnali in **pesi target** del portafoglio. Si parte da un baseline semplice (media pesata di rank) e si passa al gradient boosting solo se batte il baseline in validazione (vedi [validazione](validazione.md)). Ogni tentativo finisce nel **registro degli esperimenti** (G-12).

### ④ Motore — `engine/` (Rust)
- `money-core` (libreria): **guardrails**, macchina a stati del rischio (Attivo → Sospeso a -15% → Bloccato a -50%), modello costi (commissioni, spread, Tobin tax, cambio), modello fiscale italiano (zainetto per categoria, ETF come redditi di capitale, bollo), sizing (Kelly frazionario con tetto, volatility targeting).
- `money-engine` (binario): legge i pesi target, calcola gli ordini, li fa passare dai guardrails e li esegue tramite un **adapter**:
  - `SimBroker`: paper interno, con i costi reali di Trade Republic simulati;
  - `AlpacaPaper`: paper su un broker vero, per testare l'esecuzione;
  - `ManualTap`: crea una **proposta** (strumento, quantità, prezzo limite, scadenza) e la notifica; l'utente esegue su Trade Republic e conferma il fill dal telefono;
  - futuro: `Saxo` / `IBKR` per l'automazione totale.
- `money-py` (binding PyO3): espone `money-core` ai backtest Python.

### ⑤ Agente fiscale — Claude Code + `knowledge/fisco/`
- Knowledge base in markdown: ogni norma ha fonte, data e data dell'ultima verifica.
- Report deterministici generati da `money-core` sul ledger: plusvalenze e minusvalenze per categoria, scadenze dello zainetto, bollo, quadri RT/RW (solo in modalità dichiarativa).
- Claude spiega, controlla la coerenza e segnala i dubbi. Ogni output porta l'avviso di verifica con un commercialista.

### ⑥ API e webapp — `web/` (TypeScript)
- API (Hono, Node) in sola lettura sul DB, più gli endpoint per approvare le proposte e confermare i fill.
- Webapp (React + Vite, PWA): portafoglio, segnali spiegati, proposte da eseguire, stato dei guardrails, tasse maturate.
- Notifiche: bot Telegram (gratis) e Web Push.
- Esposizione: Cloudflare Tunnel con Cloudflare Access (login), senza porte aperte sulla VM.

## Ciclo operativo (esempio giornaliero)
1. 06:00 ingest → 2. segnali → 3. combiner → pesi target
4. Il motore calcola gli ordini, applica i guardrails, esegue (paper) o crea proposte (hybrid)
5. Notifica: "Compra 0,12 VWCE limite 118,50 € entro ven 18:00 — motivo: …"
6. Tap su Trade Republic → conferma del fill nella webapp → ledger
7. Heartbeat e report; se qualcosa è fermo o vecchio, il sistema non opera e avvisa (G-10)

La frequenza vera (giornaliera, settimanale o mensile) la sceglie il backtest.

## Hosting e operatività
- **Oracle Cloud Always Free:** VM ARM con 2 OCPU e 12 GB; Docker Compose con Postgres, motore, job Python e API.
  - Rischio: Oracle può recuperare le istanze inattive. Mitigazione da verificare: passare l'account a Pay-As-You-Go (le risorse Always Free restano gratuite).
- **Backup:** dump notturno del DB cifrato verso un repo privato o un object storage gratuito.
- **Watchdog:** GitHub Actions controlla l'heartbeat ogni ora e avvisa su Telegram se manca.
- **Segreti:** solo in `.env` sulla VM o nei secret di GitHub, mai nel repo (G-14).

## Struttura del repo
```
money/
├── CLAUDE.md                 regole per Claude (incluso il ruolo di agente fiscale)
├── config/guardrails.toml    limiti di rischio (letti dal motore, validati all'avvio)
├── docs/                     requisiti, raccolta, progettazione, ADR
├── engine/                   Rust workspace: money-core, money-engine, (money-py)
├── research/                 Python (uv): ingest, signals, combiner, backtest, notebooks
├── web/                      TypeScript: api + webapp
├── knowledge/fisco/          knowledge base fiscale con fonti
├── infra/                    docker-compose, provisioning Oracle, backup
└── .github/workflows/        CI (test Rust/Python/TS), watchdog, backup
```
