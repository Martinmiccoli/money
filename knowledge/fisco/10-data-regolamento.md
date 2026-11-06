# 10 — Quale data fa fede per l'anno fiscale
- **Ultima verifica:** 2026-11-07 · **Codice:** `Event::Fill.settlement_date`, `tax::settlement_estimate`
- **Fonte:** circ. AdE 19/E/2014 §5.1 e 11/E/2012 p. 68 (OICR: "alla data di regolamento"); [decisione ABF Milano n. 8876 del 02/10/2025](https://www.dirittobancario.it/wp-content/uploads/2026/02/Decisione-ABF-Milano-02-ottobre-2025-n.-8876.pdf)

- **ETF/OICR:** vale la **data di regolamento**. ✅
- **Azioni e altri RD:** non c'è un testo dell'AdE. Nel caso ABF una banca ha tassato nel 2025 una vendita del 30/12/2024 regolata il 2/1/2025, e così le perdite in scadenza sono andate perse. L'ABF si è dichiarato incompetente. 🟡
- **Scelta del motore (prudente):** per tutte le vendite vale il regolamento. Se manca nel fill, si stima a T+2 lavorativi, saltando weekend, 1/1, 1/5, 25/12 e 26/12. Il report avvisa per ogni vendita attribuita all'anno successivo e per le vendite dopo il 20/12 senza data di regolamento.
- **Regola pratica:** per usare perdite in scadenza, vendere **entro metà dicembre**.
