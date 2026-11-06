# 03 — Zainetto fiscale
- **Ultima verifica:** 2026-11-07 · **Codice:** `tax::TaxEngine::use_losses`, `TaxRules::loss_expiry`
- **Fonte:** art. 68 c. 5 TUIR → art. 77 c. 5; art. 6 c. 5 D.Lgs. 461/97 → art. 306 c. 6 nuovo TUIR (testo letto in GU)

1. **Scadenza:** una perdita dell'anno N è utilizzabile fino al **31/12 dell'anno N+4** ("nei successivi ma non oltre il quarto"). ✅
2. **Solo operazioni successive:** in amministrato una perdita compensa solo le plusvalenze realizzate **dopo** di essa ("nelle successive operazioni"). Le imposte pagate prima nello stesso anno **non vengono restituite**. La compensazione di fine anno esiste solo nel regime dichiarativo. ✅
3. **Ordine di consumo:** il motore usa prima le perdite più vecchie. È la scelta logica per ridurre le scadenze, ma **nessuna norma la prescrive** per l'amministrato: le circolari 11/E/2012 §12.3 e 19/E/2014 la fissano solo per i casi transitori. 🟡 Da verificare sul rendiconto di Trade Republic.
4. **Panieri separati:** le perdite crypto spot compensano solo plusvalenze crypto (art. 77 c. 11 nuovo TUIR). ✅
5. Lo zainetto vive presso il singolo intermediario: si trasferisce solo chiudendo il rapporto.
