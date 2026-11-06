# M4 — Strategie su ETF: trend (S3), rotazione (S4), regime (S8)

- **Generato il:** 2026-11-07 · **codice:** `361758b8c2a1-dirty`
- **Periodo:** 2017-01-03 → 2024-08-30 (periodo di ricerca, in-sample)
- **Hold-out:** dal 2024-09-02 — **non usato** · **dati:** `f5145c9bfdf018cd`

> Risultati simulati su dati storici: **non sono una previsione** né una promessa di rendimento. I numeri fiscali sono stime del motore e vanno verificati da un commercialista.

## In breve

- **1.000 €** — benchmark: CAGR netto 7,6%, Sharpe 0,46, drawdown -34,2%.
  - S3 — Trend following multi-asset (TSMOM): **non riesce a operare** (al massimo 5 ordini in 8 anni): i guardrails G-05/G-06 bloccano ordini troppo piccoli rispetto ai costi.
  - S4 — Rotazione momentum sui settori (migliore: top 2, isteresi): CAGR 1,2%, Sharpe 0,12, drawdown -23,5%, 30 ordini — **non batte** il benchmark (-6,4%/anno).
  - S3 + S4 con il regime S8: **non riesce a operare** (al massimo 4 ordini in 8 anni): i guardrails G-05/G-06 bloccano ordini troppo piccoli rispetto ai costi.
- **10.000 €** — benchmark: CAGR netto 7,6%, Sharpe 0,46, drawdown -34,2%.
  - S3 — Trend following multi-asset (TSMOM) (migliore: mensile, pesi uguali): CAGR 2,8%, Sharpe 0,50, drawdown -8,0%, 105 ordini — **non batte** il benchmark (-4,8%/anno).
  - S4 — Rotazione momentum sui settori (migliore: top 3, isteresi): CAGR 3,1%, Sharpe 0,30, drawdown -19,2%, 97 ordini — **non batte** il benchmark (-4,5%/anno).
  - S3 + S4 con il regime S8 (migliore: S3+S4 con regime S8): CAGR 1,8%, Sharpe 0,32, drawdown -8,3%, 148 ordini — **non batte** il benchmark (-5,7%/anno).
- **50 €** — benchmark: CAGR netto 7,5%, Sharpe 0,45, drawdown -34,2%.
  - S3 — Trend following multi-asset (TSMOM): **non riesce a operare** (al massimo 0 ordini in 8 anni): i guardrails G-05/G-06 bloccano ordini troppo piccoli rispetto ai costi.
  - S4 — Rotazione momentum sui settori: **non riesce a operare** (al massimo 0 ordini in 8 anni): i guardrails G-05/G-06 bloccano ordini troppo piccoli rispetto ai costi.
  - S3 + S4 con il regime S8: **non riesce a operare** (al massimo 0 ordini in 8 anni): i guardrails G-05/G-06 bloccano ordini troppo piccoli rispetto ai costi.
- **Gate 0 (in-sample):** nessuna variante supera tutte le soglie.

![grafico](2026-11-07-m4-strategie-etf.png)

## S3 — Trend following multi-asset (TSMOM)

| Variante | Capitale | Liquidato | CAGR netto | vs benchmark | Sharpe | Max DD | Ordini | Rifiuti principali | Interessi | DSR | PBO |
|---|---|---|---|---|---|---|---|---|---|---|---|
| mensile, vol scaling | 1.000 € | 1.044,07 € | 0,6% | -7,0% | 0,36 | -0,3% | 1 | G-06×692, G-10×154, MERCATO×27 | 60,91 € | 63,7% | 1,00 |
| mensile, pesi uguali | 1.000 € | 1.045,97 € | 0,6% | -7,0% | 0,45 | 0,0% | 0 | G-06×864, G-10×181, MERCATO×31 | 62,11 € | 74,6% | 1,00 |
| settimanale, vol scaling | 1.000 € | 1.033,37 € | 0,4% | -7,2% | -0,01 | -1,2% | 5 | G-06×3170, G-10×659, G-05×93 | 61,36 € | 25,2% | 1,00 |
| settimanale, pesi uguali | 1.000 € | 1.045,97 € | 0,6% | -7,0% | 0,45 | 0,0% | 0 | G-06×3798, G-10×752, MERCATO×89 | 62,11 € | 68,7% | 1,00 |
| mensile, vol scaling | 10.000 € | 10.889,26 € | 1,1% | -6,5% | 0,28 | -3,3% | 94 | G-06×743, G-10×192, MERCATO×29 | 366,20 € | 49,0% | 0,56 |
| mensile, pesi uguali | 10.000 € | 12.326,54 € | 2,8% | -4,8% | 0,50 | -8,0% | 105 | G-06×660, G-10×180, MERCATO×27 | 347,84 € | 72,0% | 0,56 |
| settimanale, vol scaling | 10.000 € | 11.169,80 € | 1,5% | -6,1% | 0,46 | -4,0% | 219 | G-06×3687, G-10×884, MERCATO×91 | 410,62 € | 68,1% | 0,56 |
| settimanale, pesi uguali | 10.000 € | 11.278,43 € | 1,6% | -6,0% | 0,28 | -7,0% | 243 | G-06×3379, G-10×852, MERCATO×76 | 378,22 € | 48,8% | 0,56 |
| mensile, vol scaling | 50 € | 52,32 € | 0,6% | -6,9% | 0,46 | 0,0% | 0 | — | 3,10 € | 70,8% | n/d |
| mensile, pesi uguali | 50 € | 52,32 € | 0,6% | -6,9% | 0,46 | 0,0% | 0 | — | 3,10 € | 71,0% | n/d |
| settimanale, vol scaling | 50 € | 52,32 € | 0,6% | -6,9% | 0,46 | 0,0% | 0 | — | 3,10 € | 71,2% | n/d |
| settimanale, pesi uguali | 50 € | 52,32 € | 0,6% | -6,9% | 0,46 | 0,0% | 0 | — | 3,10 € | 71,4% | n/d |

## S4 — Rotazione momentum sui settori

| Variante | Capitale | Liquidato | CAGR netto | vs benchmark | Sharpe | Max DD | Ordini | Rifiuti principali | Interessi | DSR | PBO |
|---|---|---|---|---|---|---|---|---|---|---|---|
| top 3, isteresi | 1.000 € | 1.107,01 € | 1,3% | -6,2% | 0,33 | -6,6% | 5 | G-06×606, G-10×137, MERCATO×24 | 49,20 € | 58,7% | 0,06 |
| top 3, senza isteresi | 1.000 € | 1.069,24 € | 0,9% | -6,7% | 0,15 | -9,7% | 7 | G-06×606, G-10×139, MERCATO×24 | 49,18 € | 40,5% | 0,06 |
| top 2, isteresi | 1.000 € | 1.092,25 € | 1,2% | -6,4% | 0,12 | -23,5% | 30 | G-06×242, G-10×70, MERCATO×10 | 9,34 € | 36,9% | 0,06 |
| top 2, senza isteresi | 1.000 € | 1.048,67 € | 0,6% | -7,0% | 0,07 | -23,5% | 38 | G-06×242, G-10×74, MERCATO×12 | 9,72 € | 30,5% | 0,06 |
| top 3, isteresi | 10.000 € | 12.606,67 € | 3,1% | -4,5% | 0,30 | -19,2% | 97 | G-06×266, G-10×99, MERCATO×14 | 114,46 € | 54,3% | 0,62 |
| top 3, senza isteresi | 10.000 € | 11.907,79 € | 2,3% | -5,3% | 0,23 | -19,2% | 114 | G-06×249, G-10×99, MERCATO×13 | 109,86 € | 46,5% | 0,62 |
| top 2, isteresi | 10.000 € | 11.802,84 € | 2,2% | -5,4% | 0,21 | -22,8% | 71 | G-06×195, G-10×75, MERCATO×10 | 105,92 € | 44,7% | 0,62 |
| top 2, senza isteresi | 10.000 € | 12.417,88 € | 2,9% | -4,7% | 0,25 | -22,7% | 90 | G-06×148, G-10×75, MERCATO×12 | 115,74 € | 49,7% | 0,62 |
| top 3, isteresi | 50 € | 52,32 € | 0,6% | -6,9% | 0,46 | 0,0% | 0 | — | 3,10 € | 74,8% | n/d |
| top 3, senza isteresi | 50 € | 52,32 € | 0,6% | -6,9% | 0,46 | 0,0% | 0 | — | 3,10 € | 73,7% | n/d |
| top 2, isteresi | 50 € | 52,32 € | 0,6% | -6,9% | 0,46 | 0,0% | 0 | — | 3,10 € | 72,8% | n/d |
| top 2, senza isteresi | 50 € | 52,32 € | 0,6% | -6,9% | 0,46 | 0,0% | 0 | — | 3,10 € | 72,1% | n/d |

## S3 + S4 con il regime S8

| Variante | Capitale | Liquidato | CAGR netto | vs benchmark | Sharpe | Max DD | Ordini | Rifiuti principali | Interessi | DSR | PBO |
|---|---|---|---|---|---|---|---|---|---|---|---|
| S3+S4 con regime S8 | 1.000 € | 1.045,97 € | 0,6% | -7,0% | 0,45 | 0,0% | 0 | G-06×693, G-10×153, MERCATO×27 | 62,11 € | 84,3% | 0,06 |
| S3+S4 senza regime | 1.000 € | 1.049,83 € | 0,6% | -6,9% | 0,40 | -1,2% | 4 | G-06×683, G-10×152, MERCATO×27 | 62,34 € | 77,6% | 0,06 |
| S3+S4 con regime S8 | 10.000 € | 11.503,08 € | 1,8% | -5,7% | 0,32 | -8,3% | 148 | G-06×648, G-10×186, MERCATO×34 | 293,61 € | 70,5% | 0,68 |
| S3+S4 senza regime | 10.000 € | 11.306,64 € | 1,6% | -6,0% | 0,23 | -8,8% | 144 | G-06×706, G-10×197, MERCATO×34 | 242,65 € | 61,6% | 0,68 |
| S3+S4 con regime S8 | 50 € | 52,32 € | 0,6% | -6,9% | 0,46 | 0,0% | 0 | — | 3,10 € | 83,9% | n/d |
| S3+S4 senza regime | 50 € | 52,32 € | 0,6% | -6,9% | 0,46 | 0,0% | 0 | — | 3,10 € | 83,7% | n/d |

## Gate 0 in-sample — migliore variante per famiglia (1.000 €)

Indicativo: il Gate 0 vero si misura **una volta sola** sull'hold-out.

**S3 — Trend following multi-asset (TSMOM) — settimanale, vol scaling**

| Metrica | Soglia | Valore | Esito |
|---|---|---|---|
| Sharpe netto | > 1,0 | -0,01 | ❌ |
| Max drawdown | < 15% | -1,2% | ✅ |
| Rendimento netto vs benchmark | > 0 | -7,2% | ❌ |
| Deflated Sharpe Ratio | > 95% | 25,2% | ❌ |
| Numero di trade | ≥ 30 | 5 | ❌ |
| PBO | < 0,5 | 1,00 | ❌ |

**S4 — Rotazione momentum sui settori — top 2, isteresi**

| Metrica | Soglia | Valore | Esito |
|---|---|---|---|
| Sharpe netto | > 1,0 | 0,12 | ❌ |
| Max drawdown | < 15% | -23,5% | ❌ |
| Rendimento netto vs benchmark | > 0 | -6,4% | ❌ |
| Deflated Sharpe Ratio | > 95% | 36,9% | ❌ |
| Numero di trade | ≥ 30 | 30 | ✅ |
| PBO | < 0,5 | 0,06 | ✅ |

**S3 + S4 con il regime S8 — S3+S4 senza regime**

| Metrica | Soglia | Valore | Esito |
|---|---|---|---|
| Sharpe netto | > 1,0 | 0,40 | ❌ |
| Max drawdown | < 15% | -1,2% | ✅ |
| Rendimento netto vs benchmark | > 0 | -6,9% | ❌ |
| Deflated Sharpe Ratio | > 95% | 77,6% | ❌ |
| Numero di trade | ≥ 30 | 4 | ❌ |
| PBO | < 0,5 | 0,06 | ✅ |

## Diagnostica a 10.000 €

Con più capitale gli ordini sono più grandi, le commissioni fisse pesano meno e G-05/G-06 bloccano meno: questa colonna dice se la **strategia in sé** ha valore, al netto del vincolo dei 50 €.

## Ipotesi del modello

- Periodo di ricerca dal primo giorno di borsa del 2017 (il 2016 serve come storia per i segnali a 12 mesi) fino all'inizio dell'hold-out, che resta intatto. Benchmark sullo stesso periodo.
- Proxy USA rettificati in EUR con drag annuo stimato; obbligazioni globali trattate come coperte in EUR (nessuna conversione) con 160 bp/anno di costo di copertura stimato (`config/validation.toml`).
- Decisione alle 9:00 con i soli dati pubblicati (G-11); controllo dei guardrails con il prezzo noto alla decisione; esecuzione all'apertura con metà spread e 1 € di commissione (ordini normali).
- `expected_edge_pct` (G-06): rendimento medio realizzato a 63 giorni per livello di segnale, stimato solo sul passato e **dimezzato**. Finché ci sono meno di 24 osservazioni la strategia non compra.
- Banda di non-trading 50 € (G-05 con 1 € di commissione), cuscinetto di liquidità 1%, massimo 3 ordini al giorno (G-07); i pesi si inseguono per 5 giorni di borsa dopo il ribilanciamento.
- Interessi sulla liquidità al tasso €STR quando positivo, tassati al 26%; bollo 0,2% annuo; imposte al realizzo trattenute come farebbe il broker; liquidazione finale inclusa nel CAGR netto.
- Sharpe con rf = €STR: tra il 2016 e il 2022 l'€STR era negativo, quindi una variante che resta in liquidità ha uno Sharpe (e un DSR) positivo senza fare nulla. Per questo la 'migliore variante' si sceglie solo tra quelle con almeno 30 ordini.
- PBO 'n/d': le varianti della famiglia hanno rendimenti praticamente identici (es. tutte ferme in liquidità), quindi la probabilità di overfitting non è definita.

## Registro dei tentativi (G-12)

- #48 benchmark: benchmark, 1000 €
- #49 benchmark: benchmark, 10000 €
- #50 benchmark: benchmark, 50 €
- #51 s3-tsmom: mensile, vol scaling, 1000 €
- #52 s3-tsmom: mensile, pesi uguali, 1000 €
- #53 s3-tsmom: settimanale, vol scaling, 1000 €
- #54 s3-tsmom: settimanale, pesi uguali, 1000 €
- #55 s3-tsmom: mensile, vol scaling, 10000 €
- #56 s3-tsmom: mensile, pesi uguali, 10000 €
- #57 s3-tsmom: settimanale, vol scaling, 10000 €
- #58 s3-tsmom: settimanale, pesi uguali, 10000 €
- #59 s3-tsmom: mensile, vol scaling, 50 €
- #60 s3-tsmom: mensile, pesi uguali, 50 €
- #61 s3-tsmom: settimanale, vol scaling, 50 €
- #62 s3-tsmom: settimanale, pesi uguali, 50 €
- #63 s4-rotation: top 3, isteresi, 1000 €
- #64 s4-rotation: top 3, senza isteresi, 1000 €
- #65 s4-rotation: top 2, isteresi, 1000 €
- #66 s4-rotation: top 2, senza isteresi, 1000 €
- #67 s4-rotation: top 3, isteresi, 10000 €
- #68 s4-rotation: top 3, senza isteresi, 10000 €
- #69 s4-rotation: top 2, isteresi, 10000 €
- #70 s4-rotation: top 2, senza isteresi, 10000 €
- #71 s4-rotation: top 3, isteresi, 50 €
- #72 s4-rotation: top 3, senza isteresi, 50 €
- #73 s4-rotation: top 2, isteresi, 50 €
- #74 s4-rotation: top 2, senza isteresi, 50 €
- #75 s3s4-s8: S3+S4 con regime S8, 1000 €
- #76 s3s4-s8: S3+S4 senza regime, 1000 €
- #77 s3s4-s8: S3+S4 con regime S8, 10000 €
- #78 s3s4-s8: S3+S4 senza regime, 10000 €
- #79 s3s4-s8: S3+S4 con regime S8, 50 €
- #80 s3s4-s8: S3+S4 senza regime, 50 €

---

Risultati simulati su dati storici: **non sono una previsione** né una promessa di rendimento. I numeri fiscali sono stime del motore e vanno verificati da un commercialista.
