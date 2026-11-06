# 3.1 — Specifica dei segnali

Ogni segnale produce record nel formato unico:
```
Signal { signal_id, instrument, as_of, available_at, horizon_days, score ∈ [-1,1], confidence ∈ [0,1], expected_edge_pct, pillar, explain }
```
- `available_at` è l'istante in cui **l'informazione era pubblica** (es. accettazione del filing SEC). Backtest e motore possono usare un segnale solo **dalla prima apertura di mercato successiva** ad `available_at` (G-11).
- `expected_edge_pct` è il rendimento atteso netto all'orizzonte, stimato in backtest per decile di score e **dimezzato** (shrinkage 50%). È quello che il guardrail G-06 confronta con i costi.
- `explain` è una frase in italiano che finisce nella notifica (es. "3 dirigenti hanno comprato 1,2 M$ in 6 giorni, CEO incluso").

I parametri numerici qui sotto sono **valori di partenza tratti dalla letteratura**. Si ottimizzano solo con il protocollo di [validazione](../02-progettazione/validazione.md) e ogni variante finisce nel registro esperimenti (G-12).

---

## S1 — Acquisti degli insider (Form 4) · pilastro "smart money" · priorità alta
**Evidenza:**
- Cohen-Malloy-Pomorski 2012: gli acquisti "opportunistici" hanno un alpha di circa 82 bp al mese, quelli routinari circa zero.
- Lakonishok-Lee 2001: gli acquisti predicono i rendimenti, le vendite no.
- Alldredge-Blank 2019: gli acquisti in cluster sono seguiti da oltre il 2% di rendimento anomalo nel mese successivo.

| Elemento | Specifica |
|---|---|
| Fonte | SEC EDGAR, Form 4 (`edgartools`), indice giornaliero; massimo 10 richieste al secondo, con User-Agent |
| Transazioni | Solo codice **P** (acquisto sul mercato aperto), tabella non-derivati. Esclusi: A (grant), M (esercizio), S (vendite), G (doni) e i trade marcati come **piano 10b5-1** |
| Routine vs opportunistico | Insider **routinario**: ha comprato nello stesso mese di calendario in ciascuno dei 3 anni precedenti. **Opportunistico**: ha almeno 3 anni di storia e non è routinario. **Non classificato**: ha meno storia (peso ridotto) |
| Cluster | ≥ 2 insider distinti opportunistici o non classificati con acquisti entro **10 giorni di borsa**; cluster forte se ≥ 3 |
| Pesi | ruolo (CEO/CFO/Chair 1,0 · director 0,7 · azionista >10% 0,5); valore ≥ 25 k$; Δ partecipazione (`shares_after` / `shares_before` − 1) |
| Filtri di liquidità | capitalizzazione ≥ 300 M$, prezzo ≥ 5 $, volume medio giornaliero ≥ 5 M$ (l'alpha sta nelle small cap, ma lì gli spread uccidono il retail) |
| Score | `z = 0,5·rank(n_insider) + 0,3·rank(log valore) + 0,2·rank(Δpartecipazione)`, moltiplicato per il peso del ruolo e trasformato in [0,1]. Solo long |
| `available_at` | **data/ora di accettazione del filing**, non la data della transazione (il Form 4 arriva fino a 2 giorni lavorativi dopo) |
| Orizzonte | 21 giorni di borsa (alternative da testare: 42 e 63) |
| Uscita | a fine orizzonte, con lo stop di [3.2 §Stop](02-portafoglio-e-rischio.md), oppure se un insider dello stesso cluster vende |
| Rischi noti | Decadimento dopo la pubblicazione (McLean-Pontiff). Survivorship: servono i prezzi dei titoli delistati (vedi §Problemi aperti) |

## S2 — Consenso dei superinvestor (13F) · "smart money" · universo e base di qualità
**Evidenza:**
- Cohen-Polk-Silli, "Best Ideas": le posizioni a massima convinzione dei gestori sovraperformano.
- Il clone di Berkshire ha avuto alpha storico, ma i 13F arrivano con un ritardo fino a 45 giorni.

| Elemento | Specifica |
|---|---|
| Fonte | 13F-HR da EDGAR, trimestrale |
| Lista dei gestori | Configurabile in `config/superinvestors.toml`. **Selezione point-in-time**: a ogni data un gestore è in lista solo se *a quella data* soddisfa i criteri (≥ 8 anni di 13F, portafoglio concentrato con top 10 ≥ 50%, turnover basso). Così si evita di scegliere col senno di poi chi è andato bene |
| Conviction | peso nel portafoglio del gestore meno peso del titolo nell'indice (sovrappeso), come in "Best Ideas" |
| Score | `Σ_gestori conviction`, normalizzato in rank [0,1]; bonus se la posizione è nuova o aumentata nel trimestre |
| `available_at` | data di deposito del 13F |
| Uso | (a) **universo** di qualità per S1 e per il combiner; (b) piccola quota "best ideas" con ribilanciamento trimestrale |

## S3 — Trend following time-series (TSMOM) su ETF · "matematica" · motore principale
**Evidenza:**
- Moskowitz-Ooi-Pedersen 2012: il rendimento a 12 mesi di un asset predice il suo rendimento futuro.
- Gran parte del risultato dipende dal volatility scaling.

| Elemento | Specifica |
|---|---|
| Universo | 6-8 ETF/ETC UCITS multi-asset: azionario globale, USA, emergenti, governativi EUR, inflation-linked, oro, materie prime ampie, ETP crypto (cap 15%) |
| Segnale | media dei segni dei rendimenti a 1, 3, 6 e 12 mesi (escluso l'ultimo mese per il 12): `s ∈ {0, 0.25, …, 1}` (solo long, G-03) |
| Peso | `w_i = s_i · (σ_target_asset / σ̂_i)` con σ̂ = vol EWMA a 60 giorni e σ_target_asset = 10% annuo; poi normalizzazione al budget dello sleeve, senza leva (Σw ≤ 1) |
| Ribilanciamento | mensile (l'alternativa settimanale si testa in backtest) con **banda di non-trading** (§3.2) |
| `expected_edge_pct` | stimato in backtest per livello di `s` |

## S4 — Rotazione momentum cross-section su ETF settoriali o paese · "matematica"
**Evidenza:** Jegadeesh-Titman 1993; Asness-Moskowitz-Pedersen 2013. Rischio: momentum crash (2009).

| Elemento | Specifica |
|---|---|
| Universo | 10-12 ETF UCITS settoriali (MSCI World Sectors) o paese |
| Segnale | rank del rendimento 12-1 mesi; si detengono i **top 3** a pesi uguali (1/N, DeMiguel et al.) |
| Filtro di regime | lo sleeve è investito solo se l'azionario globale è sopra la sua media mobile a 10 mesi; altrimenti va su governativi EUR o liquidità |
| Ribilanciamento | mensile, con un ETF sostituito solo se esce dalla top 5 (isteresi per ridurre il turnover) |

## S5 — Tilt fattoriale "alla Buffett" (quality + value + low-vol) · replica dei top investor
**Evidenza:** l'alpha di Buffett si spiega con i fattori quality, value e low-beta (Frazzini-Kabiller-Pedersen 2018); RMW di Fama-French 2015.

| Elemento | Specifica |
|---|---|
| Implementazione v1 | ETF UCITS fattoriali (World Quality, World Value, World Min Vol), con pesi da S3 (si investe solo il fattore in trend) |
| Implementazione v2 (opzionale) | screening sulle azioni USA dell'universo S2: ROE/ROIC, stabilità degli utili, EV/EBIT, beta basso. Fondamentali da FMP free (250 richieste al giorno) |

## S6 — Sentiment e attenzione · pilastro "reputazione, gossip, fede" · filtro e feature
**Evidenza:**
- Il pessimismo dei media si inverte in pochi giorni (Tetlock 2007).
- I picchi di attenzione retail portano a rendimenti negativi: −4,7% a 20 giorni per i titoli più comprati su Robinhood (Barber et al. 2022); Google SVI dà +2 settimane poi inversione (Da-Engelberg-Gao 2011).
- Il "mood" di Twitter (Bollen) non si replica.

| Componente | Specifica |
|---|---|
| **Attenzione** | z-score a 60 giorni di (a) numero di articoli GDELT che citano l'azienda e (b) **visualizzazioni della pagina Wikipedia** (API Wikimedia, gratuita; proxy di Google Trends, ⚠️ da validare in backtest) |
| **Tono** | FinBERT (modello locale, 0 €) sui titoli delle notizie (GDELT, Marketaux 100 richieste al giorno); media giornaliera per ticker, ponderata per fonte |
| **Uso 1: filtro anti-hype** | **veto sugli acquisti** se attenzione z > 3 nei 5 giorni precedenti, salvo cluster insider forte |
| **Uso 2: feature** | tono, Δtono e attenzione entrano come feature nel combiner ML (S-ML). Nessuna regola diretta di trading sul tono |
| **Uso 3: indice "narrazione/fede"** | quota di articoli GDELT sui temi "bolla, AI, crypto, crash, recession" rispetto al totale. Serve come variabile di regime (Shiller, *Narrative Economics*). Esplorativo |
| **Laboratorio crypto (solo paper)** | Fear & Greed di alternative.me come segnale contrarian su BTC/ETH spot, per vedere se il sentiment funziona dove pesa di più |
| Reddit / X | Esclusi in v1 (Reddit richiede approvazione dal 2025, X è a pagamento). Si rivaluta se l'accesso diventa gratuito |

## S7 — Congresso USA · segnale secondario
- Fonte: Periodic Transaction Report di Camera e Senato (PDF ufficiali).
- Solo **acquisti** di membri della leadership e di presidenti di commissione ("Captain Gains", NBER 2025). In media i membri non battono il mercato.
- `available_at` = data di pubblicazione del report, non quella del trade (fino a 45 giorni di ritardo).
- Uso: solo come feature del combiner. Il parsing dei PDF è a basso costo di priorità (milestone tarda).

## S8 — Regime di mercato · gestione del rischio
| Input | Fonte |
|---|---|
| Azionario globale sopra o sotto la media mobile a 10 mesi | prezzi |
| Volatilità realizzata dell'S&P 500 a 20 giorni rispetto alla mediana a 1 anno | prezzi |
| Curva dei tassi T10Y3M, spread di credito BAA10Y | FRED |
| Indice di narrazione (S6) | GDELT |

Output: **moltiplicatore di esposizione** degli sleeve tattici ∈ {1, 0,5, 0,25}. Il core (piano di accumulo) non viene toccato.

## S-ML — Combiner ML (livello 1, opzionale)
- Si usa **solo se batte il combiner a regole** (livello 0, [3.2](02-portafoglio-e-rischio.md)) secondo il Gate 0, con DSR calcolato su tutti i tentativi.
- Modello: LightGBM per il ranking delle azioni dell'universo S1/S2. Feature da tutti i pilastri più momentum, volatilità e liquidità (i segnali dominanti in Gu-Kelly-Xiu 2020). Label: rendimento in eccesso a 21 giorni.
- Validazione: purged K-fold con embargo di 21 giorni, walk-forward annuale.
- **Esclusi**: deep learning end-to-end, foundation model per serie temporali sui rendimenti (TimesFM e Chronos falliscono in zero-shot), LLM che decidono i trade (G-17).

## Problemi aperti (da chiudere in sviluppo)
1. **Prezzi dei titoli delistati** per S1 (survivorship bias): verificare se Alpaca li fornisce; in alternativa stimare il bias.
2. **Prezzi storici degli ETF UCITS: non esiste una fonte gratuita con ToS puliti** ([approfondimenti](../01-raccolta/approfondimenti-fase3.md)). Decisione:
   - nel backtest si usano gli **ETF USA equivalenti** (Alpaca, total return) convertiti in EUR con il cambio BCE. Errore misurato sul proxy di CSPX: circa 0,34% al giorno, senza accumulo;
   - LS-TC (endpoint JSON non documentato) si usa solo per **controlli a campione manuali**, senza salvarlo nel DB, come previsto dal suo disclaimer;
   - il prezzo corrente per la proposta è un **prezzo indicativo** calcolato da proxy + cambio. L'utente lo confronta comunque con l'app prima del tap.
3. **Mappatura CUSIP/ticker/ISIN** tra SEC, Alpaca e Trade Republic (OpenFIGI, gratuito).
