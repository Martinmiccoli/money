# Knowledge base fiscale (agente fiscale — ADR-004)
Ogni scheda descrive una regola con **fonte**, **in vigore dal**, **ultima verifica** e **dove la applica il codice**.
Il punto di partenza è [broker-e-fisco.md](../../docs/01-raccolta/broker-e-fisco.md). Le regole numeriche stanno in
[`config/fisco.toml`](../../config/fisco.toml) e il motore in `engine/crates/money-core/src/tax.rs`.

> Le informazioni qui contenute non sostituiscono un commercialista. Ogni dichiarazione va verificata da un professionista.

| # | Scheda | Stato al 2026-11-07 |
|---|---|---|
| 00 | [Riferimenti normativi e nuovo TUIR dal 2027](00-riferimenti.md) | ✅ |
| 01 | [Aliquote 26% e crypto 33%](01-aliquote.md) | ✅ (proposta di tornare al 26% per le crypto: solo bozza) |
| 02 | [Redditi diversi e redditi di capitale (asimmetria degli ETF)](02-categorie.md) | ✅ |
| 03 | [Zainetto: compensazione e scadenza](03-zainetto.md) | ✅ regola · 🟡 ordine di consumo |
| 04 | [Costo medio ponderato e commissioni](04-costo-medio.md) | ✅ · 🟡 commissioni di vendita (dedotto) |
| 05 | [ETP crypto e crypto spot](05-crypto.md) | ✅ ETP al 26% · ❌ crypto spot in amministrato su TR |
| 06 | [ETF con titoli di Stato (white list)](06-white-list.md) | ✅ · 🟡 testo consolidato del DM |
| 07 | [Dividendi USA e W-8BEN](07-dividendi-usa.md) | ✅ · 🟡 pagina TR Italia |
| 08 | [Imposta di bollo](08-bollo.md) | ✅ · 🟡 minimo di 1 € |
| 09 | [Tobin tax (FTT)](09-tobin-tax.md) | ✅ · ⚠️ raddoppio proposto per il 2027 |
| 10 | [Data che fa fede: regolamento](10-data-regolamento.md) | ✅ ETF · 🟡 azioni |

## Punti aperti da chiudere prima dei soldi veri
1. **Trade Republic:** ordine di consumo dello zainetto, base di calcolo del bollo, crypto spot in amministrato. Si verificano sul primo rendiconto fiscale reale (M10).
2. **Data di regolamento per le azioni:** il motore usa per prudenza il regolamento (T+2) per tutto.
3. **DDL Bilancio 2027 (AC 3174):** è in Parlamento. Se approvato raddoppia la Tobin tax (scheda 09); va ricontrollato a gennaio 2027.
4. Comma esatto sulla **non deducibilità della FTT** (scheda 09).
