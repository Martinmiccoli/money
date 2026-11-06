# 06 — ETF con titoli di Stato "white list"
- **Ultima verifica:** 2026-11-07 · **Codice:** `Event::Fill.white_list_pct`, `config/fisco.toml` (`white_list_taxable_share_pct = 48.08`)
- **Fonte:** DM 13/12/2011 art. 1 c. 1-4; D.L. 138/2011 art. 2; D.L. 66/2014 art. 3; circ. AdE 11/E del 28/03/2012 §8.5.1, pp. 63-67 ([PDF](https://www.agenziaentrate.gov.it/portale/documents/20143/299598/Circolare+11+28032012_Circolare+riforma+rendite+modificata+_2_.pdf/e0f1413a-2c50-25f3-8f3e-55429495fa48)); esempio di certificazione [Amundi](https://www.amundietf.it/pdfDocuments/letter-of-certification_with-letterhead_30-june-2022-signed.pdf)

- La quota del provento riferibile ai titoli di Stato white list è imponibile al **48,08%**, cioè 12,5% effettivo.
- **Anche le minusvalenze** si riducono nella stessa proporzione (DM art. 1 c. 4). Molti blog sbagliano su questo punto.
- **Formula:** rilevante = R × (1 − p) + R × p × 48,08%. Qui p è la % media di attivo white list negli ultimi due prospetti redatti entro il semestre solare precedente la vendita.
- **Chi pubblica p:** l'emittente, ogni semestre. Se p non è pubblicata vale **zero**: il motore tratta un campo vuoto come p = 0.
- **Eccezione non modellata:** la parte di risultato dovuta alla differenza tra prezzo di borsa e NAV rileva per intero. È un effetto piccolo.
- 🟡 Non ho trovato il testo consolidato del DM con il 48,08% applicato alle perdite: il valore è dedotto dal D.L. 66/2014 e dalla lettera Amundi.
- **Nel nostro universo:** riguarda `global_bonds_hedged`. Prima del live serve la % semestrale dell'emittente.
