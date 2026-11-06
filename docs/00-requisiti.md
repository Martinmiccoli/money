# Money — Requisiti (Fase 1, sessione domande del 2026-11-06)

## Obiettivo
- Capitale iniziale: 50 €.
- Obiettivo dichiarato: 500 €. Riformulato come **crescita realistica**: arrotondare ogni mese con metodo, senza puntare tutto su un 10x in 30 giorni.
- Altro capitale verrà versato **solo dopo che lo strumento è validato**.

## Criterio di validazione (statistico)
- Backtest su più anni di dati storici **e** da 1 a 3 mesi di paper trading.
- Deve battere il benchmark (ETF S&P 500) con **Sharpe > 1** e **drawdown massimo < 15%**.

## Gestione del rischio
- **Soft stop a -15%**: blocca tutta l'operatività e chiede la conferma dell'utente per ripartire.
- **Kill switch duro a -50%** (25 €): ultima difesa, il sistema si ferma senza eccezioni.

## Modalità operativa
- Si parte in **paper trading** e si passa ai soldi veri solo a validazione superata.
- Devono essere supportate le microtransazioni e le frazioni di azioni.

## Mercati
- Azioni USA, azioni UE/Italia, ETF, crypto.

## Broker
- Ancora da scegliere. Requisiti: accessibile a un residente italiano, API, frazioni di azioni, commissioni minime, ambiente di paper trading.

## Pilastri dei segnali
1. **Smart money**: top player e fondi (13F), insider (Form 4), politici USA. Nota: i dati escono con fino a 45 giorni di ritardo.
2. **Sentiment / reputazione / gossip**: news finanziarie, Reddit/social, Google Trends.
3. **Matematica e statistica**: fattori, momentum, mean reversion, risk sizing (Kelly frazionario).
4. **ML / predizioni**: modelli validati con walk-forward, nessun look-ahead bias.
5. **Letteratura**: libri, paper e SOTA come base di ogni strategia.
6. **Aggregazione**: riusare soluzioni e dati esistenti invece di reinventarli.

## Fisco
- L'utente è **lavoratore dipendente** e vuole **zero adempimenti** a fine anno → **regime amministrato** obbligatorio: il broker fa da sostituto d'imposta, trattiene le tasse e compensa le minusvalenze.
- Vincolo critico: i broker in regime amministrato offrono raramente API ufficiali, e con 50 € le commissioni pesano molto. Da verificare nella Fase 1.
- Crypto: verificare se esistono intermediari italiani in regime amministrato. In mancanza, serve la dichiarazione dei redditi (quadro RT/RW) oppure si escludono le crypto dal live.
- Agente fiscale (Claude) con una knowledge base sulle leggi italiane: plusvalenze al 26%, quadri RW/RT, IVAFE, regole crypto.
- Le informazioni fiscali vanno sempre verificate da un commercialista prima della dichiarazione.

## Vincoli tecnici
- Budget per dati e API: **0 €** (solo piani gratuiti e open source).
- Hosting: **cloud gratuito**.
- Stack: **Rust** per il motore di esecuzione e rischio, **TypeScript** per webapp, API e orchestrazione, **Python** per ML e backtest.
- Profilo utente: tecnico ma non sviluppatore. Il codice lo scrive Claude, con spiegazioni.

## Questioni aperte
- Il cloud gratuito non tiene acceso un motore Rust 24/7 senza limiti: va verificato in fase di progettazione.
