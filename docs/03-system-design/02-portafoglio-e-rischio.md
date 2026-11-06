# 3.2 — Costruzione del portafoglio, sizing e rischio

## Struttura core / satellite
| Parte | Contenuto | Esecuzione | Quota iniziale (da ottimizzare in backtest) |
|---|---|---|---|
| **Core** | ETF UCITS azionario globale (benchmark) | **Piano di accumulo** su Trade Republic: 0 € di commissioni, minimo 10 € per esecuzione, automatico, nessun tap | 60% |
| **Satellite ETF** | S3 trend + S4 rotazione + S5 fattori | Ribilanciamento mensile: proposte (hybrid) o API (live) | 30% |
| **Satellite azioni** | S1 insider (+ S2 best ideas) | Proposte puntuali | 10% |

Tra gli sleeve si parte da pesi fissi (1/N "pesato a rischio"), perché l'ottimizzazione media-varianza stimata fa peggio fuori campione (DeMiguel et al. 2009).

### Sblocco progressivo in base al capitale
G-05 (costo ≤ 2%) con 1 € di commissione impone un **ordine minimo di 50 €**. Il sistema calcola da solo cosa è attivabile:

| Capitale | Cosa si attiva nel live |
|---|---|
| < ~150 € | Solo il core con il piano di accumulo. I satellite girano **in paper in parallelo** |
| ~150-500 € | Satellite ETF, ma solo con ribilanciamenti dove ogni ordine è ≥ 50 € (in pratica 1-2 ETF alla volta) |
| > ~500 € | Satellite azioni (S1) con ordini ≥ 50 € e massimo 20% per titolo (G-08) |

Le soglie non sono scritte a mano: sono la conseguenza dei guardrails. Questa tabella le rende solo visibili.

## Combiner a regole (livello 0, baseline)
1. Ogni sleeve calcola i suoi pesi target (S3, S4, S5 producono pesi; S1 e S2 producono una lista di titoli con score).
2. Filtri: **veto anti-hype** S6 sugli acquisti; il moltiplicatore di regime S8 scala gli sleeve tattici.
3. I pesi degli sleeve vengono combinati con le quote core/satellite e la liquidità residua resta in cassa o in un ETF monetario EUR.

## Sizing
- **Volatility targeting di portafoglio:** 10-12% annuo sulla parte satellite. Serve a **controllare il rischio**, non come fonte di rendimento: l'alpha out-of-sample di Moreira-Muir è dibattuto (Cederburg et al.).
- **Kelly frazionario come tetto:** per i trade S1, `f = 0,25 · μ̂ / σ̂²` con μ̂ = `expected_edge_pct` già dimezzato. Il peso finale è il minimo tra Kelly frazionario, il peso di sleeve e il limite G-08.
- **Arrotondamento:** si usano le frazioni di azione (Trade Republic da 1 €). Un ordine sotto il minimo di costo (G-05) viene **scartato, non forzato**.

## Banda di non-trading (riduce il turnover)
Il ribilanciamento verso il peso target avviene solo se:
```
|w_target − w_attuale| · equity  >  max( 50 €,  costo_ordine / max_cost_ratio )
e  rendimento atteso del ribilanciamento  ≥  2 × costo round-trip      (G-06)
```
Altrimenti la posizione resta com'è. Per i satellite ETF si applica anche l'isteresi di S4 (si esce solo dalla top 5).

## Stop e uscite
| Sleeve | Regola |
|---|---|
| Core | Nessuno stop: orizzonte lungo; il rischio lo gestisce G-01/G-02 a livello di conto |
| Satellite ETF | Uscita data dal segnale (trend negativo al ribilanciamento). Nessuno stop intramensile |
| Satellite azioni (S1) | Stop a `prezzo_ingresso − 3 × ATR(20)`. **Sul broker solo se la posizione è in quote intere** (Trade Republic non ammette stop sulle frazioni); altrimenti stop monitorato dal sistema con notifica urgente ([3.5](05-esecuzione-hybrid.md)). Uscita a fine orizzonte |

## Guardrails di conto (già implementati in `money-core`)
- **G-01 soft stop a −15%** dal massimo: niente nuovi acquisti; serve la ripartenza esplicita dell'utente.
- **G-02 kill switch a −50%** del capitale versato: niente ordini.
- Le vendite che riducono il rischio restano sempre possibili, finché il conto non è bloccato.
