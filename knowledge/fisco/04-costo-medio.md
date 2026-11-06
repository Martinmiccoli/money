# 04 — Costo fiscale: costo medio ponderato e commissioni
- **Ultima verifica:** 2026-11-07 · **Codice:** `portfolio.rs` (`Holding.cost_eur`, `Realization`)
- **Fonte:** art. 6 D.Lgs. 461/97 → art. 306 c. 5 nuovo TUIR ("il costo o valore medio ponderato relativo a ciascuna categoria"); art. 68 c. 6 TUIR → art. 77 ("aumentato di ogni onere inerente… con esclusione degli interessi passivi"). [Brocardi, art. 68](https://www.brocardi.it/testo-unico-imposte-redditi/titolo-i/capo-vii/art68.html)

- **Costo medio ponderato** per titolo. ✅
- **Commissioni di acquisto:** si sommano al costo. ✅
- **Commissioni di vendita:** il motore le sottrae dal ricavo. Non esiste un testo esplicito: la regola è dedotta da "ogni onere inerente". 🟡
- **Tobin tax:** **non** entra nel costo (vedi scheda 09).
- Il costo residuo dopo una vendita parziale è calcolato con 8 decimali. Le plusvalenze e le imposte si arrotondano al centesimo per operazione.
