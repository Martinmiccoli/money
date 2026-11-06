# Approfondimenti fase 3: prezzi UE gratuiti, Alpaca dall'Italia, Trade Republic oggi

**Data della ricerca:** 2026-11-06
**Contesto:** capitale 50 €, budget 0 €. Soldi veri su Trade Republic (regime amministrato, esecuzione manuale con un tap), paper trading su Alpaca Paper. Questo documento completa `broker-e-fisco.md` e `fonti-dati-e-hosting.md` e non ripete quello che c'è già.

> **Legenda**
> - ✅ **VERIFICATO**: letto su una fonte ufficiale oppure provato da me oggi con una chiamata HTTP reale (lo indico con "test diretto").
> - 🟡 **PROBABILE**: più fonti secondarie concordi, nessuna conferma ufficiale.
> - ❌ **INCERTO**: fonti in conflitto, datate o assenti.
>
> Le pagine pubbliche di assistenza di Trade Republic (`support.traderepublic.com/...`) **ora reindirizzano tutte** a `traderepublic.com/<lingua>/support`, che rimanda all'assistenza in-app (test diretto). Gli articoli FAQ ufficiali sugli ordini quindi non si leggono più dal web: per quei punti uso il listino prezzi ufficiale italiano, il comunicato stampa ufficiale e fonti secondarie datate.

---

## Novità che cambiano le decisioni precedenti

1. **Trade Republic non esegue più tutto su LS Exchange.** Dal 2 luglio 2026, dopo il divieto UE di PFOF (30/06/2026), gli ordini vanno in **"Best Price"**: TR confronta le quotazioni negoziabili delle borse rilevanti ed esegue **in contropartita con sé stessa**, a 1 €. In alternativa c'è **"Direct Price"**: il cliente sceglie una di 30 borse (Xetra, Euronext, Nasdaq, NYSE...) e paga 2 €. ✅ [Comunicato TR 02/07/2026 (PDF)](https://assets.traderepublic.com/assets/files/PressRelease_Webtrading_AT_EN_2.pdf), ✅ [Listino IT v07.2026 (PDF)](https://assets.traderepublic.com/assets/files/further_information_price_list_IT.pdf), 🟡 [justETF](https://www.justetf.com/de/academy/trade-republic-news-market-maker.html), 🟡 [FinanzaOnline](https://www.finanzaonline.com/notizie/trade-republic-come-cambia-la-sua-tecnologia-di-trading).
   **Conseguenza:** il prezzo LS-X è un buon riferimento ma non è più "il" prezzo di esecuzione. Il prezzo vero è quello che l'app mostra al momento del tap.
2. **Le crypto su TR Italia sono in regime amministrato.** La pagina ufficiale italiana dice: "Trading di 50 crypto in Regime Amministrato" e "Calcoliamo, tratteniamo e versiamo le imposte sulle plusvalenze realizzate in crypto". Così si chiude il punto ❌ aperto in `broker-e-fisco.md` §1.1 e §2.2. ✅ [traderepublic.com/it-it/crypto](https://traderepublic.com/it-it/crypto) (testo letto dal payload della pagina)
3. **Il piano di accumulo su TR ha un minimo di 10 € per esecuzione** (non 1 €). Le esecuzioni dei piani sono gratuite. ✅ Listino IT v07.2026: "Volume di investimento per esecuzione: da 10 € a 10.000 €".
4. **Le frazioni restano solo a mercato, in importo.** Gli ordini limite e stop valgono solo per quote intere (🟡, vedi §3.1). Con 50 € e un ETF S&P 500 a circa 715 € (CSPX su LS-TC oggi) **il "prezzo limite" si può usare solo per strumenti con prezzo unitario sotto il budget**.

---

## 1. Prezzi gratuiti per ETF UCITS ed ETP crypto quotati in Europa

### 1.1 Tabella riassuntiva

| Fonte | Copertura UCITS / ETP | Storico giornaliero | Prezzo corrente | Limiti | ToS sull'uso automatizzato | Esito |
|---|---|---|---|---|---|---|
| **LS-TC / LS-X** (`ls-tc.de`, endpoint JSON del grafico) | ✅ test diretto: CSPX `IE00B5BMR087`, XDWD `IE00BJ0KDQ92`, ETN Bitwise Bitcoin `DE000A27Z304`, CoinShares `GB00BLD4ZL17` trovati per ISIN | ✅ test diretto: CSPX **dal 05/01/2011** (4.850 punti), ETN BTC dal 18/06/2020. **Un solo valore al giorno** (mid, niente OHLC né volumi) | ✅ test diretto: serie intraday a 1 minuto del giorno corrente, aggiornata in tempo reale o quasi. I parametri `bid` e `ask` restituiscono **gli stessi valori del `mid`**: dallo spread non si ricava nulla | Nessun limite pubblicato. Endpoint **non documentato**: può cambiare senza preavviso | `ls-tc.de/robots.txt`: `Allow: /`. `ls-x.de/robots.txt`: `Disallow: /`. Disclaimer LS-TC: consentiti "copie e download per uso personale, privato e non commerciale", ma l'"Einspeicherung... in Datenbanken" (salvataggio in database) richiede consenso scritto | 🟡 **zona grigia**: tecnicamente è la migliore, legalmente borderline |
| **Stooq** (nuova API key) | Storicamente ticker `.DE`, `.UK` ecc. Copertura ETP non verificata | Lungo (EOD) | No (EOD) | Quota giornaliera non dichiarata | Da marzo 2026 serve `&apikey=` ottenuta risolvendo un CAPTCHA su `stooq.com/q/d/?s=...&get_apikey`. **Test diretto:** senza chiave `q/d/l/` restituisce una pagina JS con proof-of-work, non il CSV. ToS ufficiali non trovati | ❌ [pandas-datareader #1012](https://github.com/pydata/pandas-datareader/issues/1012), [apievangelist](https://providers.apievangelist.com/providers/stooq/), [guida qiita](https://qiita.com/katafuchix/items/c74793e5041e1b5e3051). Utilizzabile con chiave manuale, fragile |
| **Tradegate BSX** (ex Tradegate Exchange, fusa con Börse Berlin dall'01/01/2026) | ✅ test diretto: `tradegate.de/refresh.php?isin=...` restituisce JSON con bid/ask/last/size | No (nessun download storico trovato) | ✅ bid/ask reali (unica fonte gratuita con lo spread vero) | — | ⛔ **Vietato esplicitamente**: "Die Nutzung des Internetangebots durch automatisiert bzw. maschinell erzeugte Zugriffe, bspw. mit Hilfe von Programmen oder Skripten, ist nicht gestattet". Vietato anche salvare prezzi senza consenso scritto | ✅ [nutzungsbedingung.php](https://www.tradegatebsx.com/nutzungsbedingung.php), [fusione](https://www.broker-test.at/news/fusion-von-tradegate-exchange-und-boerse-berlin-zu-tradegate-bsx-ab-2026/). **Da escludere** |
| **Börse Frankfurt / live.deutsche-boerse.com** | Xetra + Frankfurt | Sì via API interna `api.boerse-frankfurt.de` | Ritardato | **Test diretto:** senza gli header calcolati dal JS del sito l'API risponde `{}`. Esistono librerie non ufficiali (bf4py) | Nel disclaimer non ho trovato una clausola esplicita sull'automazione (solo divieti su dati ESG). L'API ufficiale è il "Deutsche Börse API Platform", a pagamento con chiave | ❌ sconsigliato (reverse engineering, ToS non chiari) |
| **Deutsche Börse Public Data Set (AWS)** | Xetra, Eurex (barre a 1 minuto) | Storico | — | — | Il registro AWS dice: "The provider of this dataset will no longer maintain this dataset" | ✅ [registry.opendata.aws](https://registry.opendata.aws/deutsche-boerse-pds/). **Morto**; nessun successore gratuito trovato |
| **justETF** | ETF UCITS ed ETP crypto | ✅ test diretto: `justetf.com/api/etfs/{ISIN}/performance-chart?...` restituisce una serie giornaliera (prezzi Xetra in EUR, **con i weekend riempiti** col valore del venerdì) | ✅ test diretto: `.../quote` restituisce l'ultimo prezzo e la sede (`XETRA`) | Endpoint **non documentato** | `robots.txt` blocca solo `/servlet/` e `/link/`. Le condizioni generali sono in un PDF che non sono riuscito a estrarre: **ToS non verificati** | ❌ utile come controllo manuale; non come fonte primaria |
| **Twelve Data (Basic, gratis)** | ✅ verificato via API `/exchanges?show_plan=true`: **XETR, XFRA, XLON → piano "Grow"; XMIL → piano "Pro"**. Nessuna borsa UE nel piano gratuito | — | Solo USA, forex e crypto nel gratuito | 8 crediti/min, 800/giorno | "Internal non-display usage" | ✅ [pricing](https://twelvedata.com/pricing). **Inutile per l'UE**, ma **utile per il cambio EUR/USD in tempo reale** (forex incluso nel gratuito) |
| **EODHD (free)** | Borse UE nel catalogo (ticker `.XETRA`) | **1 anno** | Ritardo di 15 minuti | **20 chiamate/giorno** più 500 di benvenuto | Non specificato per il free | ✅ [pricing](https://eodhd.com/pricing). Troppo poco per il backtest |
| **Finnhub (free)** | Internazionali **a pagamento** secondo più fonti; anche le candele USA risultano bloccate sul free | — | — | ~60/min | — | 🟡 [issue #546](https://github.com/finnhubio/Finnhub-API/issues/546). Da escludere |
| **yfinance / Yahoo** | `SXR8.DE`, `CSPX.L`, `BTCE.DE` ecc. | Lungo | Ritardato | **Test diretto oggi:** HTTP **429 Too Many Requests** alla prima chiamata dal mio IP | ToS Yahoo contrari all'accesso automatizzato (vedi `fonti-dati-e-hosting.md`) | 🟡 fragile e contro i ToS |
| **BCE (cambio di riferimento)** | EUR/USD giornaliero alle 14:15 CET | ✅ test diretto: `data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A?format=csvdata` | — | Nessuno pubblicato | Riuso consentito citando la fonte | ✅ |
| **FRED** (`SP500`, `DEXUSEU`) | Indice S&P 500 (solo prezzo, 10 anni) e cambio noon New York | ✅ test diretto: `fred.stlouisfed.org/graph/fredgraph.csv?id=SP500` scarica il CSV **senza chiave** | — | — | `SP500` ha copyright S&P: uso personale | ✅ |

### 1.2 Conclusione sui prezzi

**Non esiste una fonte gratuita, documentata e con ToS puliti per lo storico giornaliero degli ETF UCITS e degli ETP crypto europei.** Le uniche che funzionano oggi in modo automatico (LS-TC e justETF) usano endpoint non documentati. Per LS-TC il disclaimer consente download personali e non commerciali, ma non il salvataggio in database senza consenso. Tradegate lo vieta in modo esplicito.

**Proposta pragmatica, in ordine:**

1. **Backtest = proxy pulito (fonte primaria).**
   - **ETF azionari:** sottostante USA via **Alpaca Market Data** (storico dal 2016, gratis con l'account paper, ToS chiari), convertito in EUR con il cambio. Esempi: SPY per CSPX/SXR8, URTH o ACWI per i MSCI World. Per lo storico più lungo: `SP500` di FRED.
   - **Cambio:** per lo storico BCE (ufficiale e riusabile) oppure FRED `DEXUSEU` (fixing più vicino alla chiusura USA, quindi meno rumore; vedi §1.3). In tempo reale Twelve Data free (forex incluso).
   - **ETP crypto:** BTC/EUR spot da `data.binance.vision` o Kraken (già in `fonti-dati-e-hosting.md`), meno il TER dell'ETP pro rata giornaliero (il TER va letto sul KID del singolo prodotto, non l'ho verificato).
2. **Validazione = LS-TC**, a bassissima frequenza (una chiamata per ISIN a settimana, uso personale) per **misurare** l'errore del proxy, senza farne la fonte di verità del sistema. Se si vuole stare del tutto puliti, scrivere a Lang & Schwarz e chiedere il consenso (l'indirizzo è nel loro impressum).
3. **Prezzo per la proposta = quello dell'app TR al momento del tap.** Visto che (a) dal 02/07/2026 l'esecuzione Best Price è contro TR e non su una borsa precisa e (b) le frazioni vanno solo a mercato, la proposta deve contenere **importo in €, ISIN e una soglia di validità**, per esempio: "esegui solo se il prezzo in app è ≤ riferimento × (1 + 0,5%)". Il riferimento è il proxy convertito (o LS-TC). L'utente controlla il prezzo in app e decide. Per le quote intere si può anche inserire un vero ordine limite.

### 1.3 Stima dell'errore del proxy (misurata oggi, non stimata a occhio)

**Metodo:** CSPX in EUR (LS-TC, valore giornaliero) confrontato con l'indice S&P 500 di FRED convertito in EUR. Periodo dal 06/11/2023 al 05/11/2026, circa 730 giorni comuni. Script: `te.py` nella cartella scratchpad della sessione (non salvato nel progetto).

| Cambio usato | Scarto giornaliero (dev. std) | Scarto medio assoluto | 95° percentile | Scarto su 20 giorni (dev. std) | Deriva cumulata |
|---|---|---|---|---|---|
| FRED `DEXUSEU` (noon NY) | **0,34%** | 0,23% | 0,68% | 0,34% | +2,9% in 3 anni (**circa +0,96%/anno**) |
| BCE 14:15 CET | 0,51% | 0,38% | 1,06% | 0,49% | +2,7% in 3 anni (circa +0,90%/anno) |

**Come leggerla:**
- Lo scarto giornaliero è soprattutto **rumore di orario**: l'ETF chiude su LS intorno alle 22-23 CET, l'indice alle 22 CET, il cambio è fissato a mezzogiorno NY o alle 14:15 CET. **Non si accumula**: su 20 giorni la deviazione resta circa 0,34%. Con il fixing BCE il rumore sale di circa il 50%.
- La **deriva di circa +0,9-1%/anno** è dovuta ai **dividendi**: `SP500` è un indice di solo prezzo, CSPX è ad accumulazione. Con SPY e dividendi reinvestiti (total return) la deriva dovrebbe scendere a circa ±0,1-0,3%/anno (TER e ritenuta sui dividendi). **Questo valore non l'ho misurato** perché oggi non avevo dati SPY gratuiti senza chiave: va ricalcolato con Alpaca. ❌
- **Per il motore:** usare un margine di errore di prezzo di circa **±0,7% (p95, giornaliero)** sul riferimento proxy. Per segnali su orizzonti di giorni o settimane il proxy va bene; per decisioni intraday no.
- Il timestamp del valore giornaliero LS-TC (00:00 UTC) non chiarisce a che ora si riferisca il prezzo (probabilmente la chiusura serale). ❌

---

## 2. Alpaca da residente italiano

| Domanda | Risposta | Stato |
|---|---|---|
| Account paper-only con sola email? | **Sì.** "Anyone globally can create an Alpaca Paper Only Account! All you need to do is sign up with your email address." | ✅ [docs.alpaca.markets/docs/paper-trading](https://docs.alpaca.markets/docs/paper-trading) |
| Market Data API gratis? | **Sì, piano Basic**, che "serves as the default option for both Paper and Live trading accounts". Azioni: realtime solo IEX, WebSocket 30 simboli, storico dal 2016 **escluso l'ultimo quarto d'ora**, 200 chiamate/min. Lo storico crypto non richiede nemmeno l'autenticazione. | ✅ [about-market-data-api](https://docs.alpaca.markets/docs/about-market-data-api) |
| Restrizioni per i non USA? | Per il paper la documentazione non ne pone. Precisa però che chi ha un account paper-only "is only entitled to receive and make use of IEX market data". Unica esclusione nota sui dati: gli abbonamenti dati a pagamento **non sono offerti ai residenti in Canada** (forum). Italia mai citata come esclusa. | ✅ IEX-only / 🟡 [forum Canada](https://forum.alpaca.markets/t/is-the-market-data-subscription-available-in-canada/19519) |
| Conto live dall'Italia? | La pagina ufficiale dei paesi (febbraio 2026) **non elenca i paesi** e rimanda al supporto. Non serve al progetto (il live è su TR). | ❌ [countries](https://alpaca.markets/support/countries-alpaca-is-available) |
| Paper-only + piano SIP a pagamento? | Fonti in conflitto (la doc ufficiale dice solo IEX, il forum dice che funziona). Irrilevante con budget 0 €. | ❌ |

**Implicazione:** Alpaca Paper copre solo azioni ed ETF **USA** più crypto. Il paper trading del motore userà quindi i **proxy USA** (SPY ecc.), cioè gli stessi strumenti del backtest al §1.2. Il modello di costo deve simulare TR: 1 € per ordine, piani gratuiti da 10 €, spread.

---

## 3. Trade Republic Italia: funzioni attuali

### 3.1 Tipi di ordine

| Funzione | Cosa risulta | Stato |
|---|---|---|
| Mercato, limite, stop (quote intere) | Sì. Il comunicato TR cita "market, limit and stop orders" anche in Direct Price | ✅ [comunicato 02/07/2026](https://assets.traderepublic.com/assets/files/PressRelease_Webtrading_AT_EN_2.pdf) |
| **Stop-limit e trailing stop** | **Nuovi** (articolo del 30/10/2026): disponibili **solo in Best Price**, con TR come sede, non in Direct Price. Rilascio graduale; nessuna garanzia di esecuzione o di prezzo. L'articolo è austriaco: **disponibilità in Italia non confermata** | 🟡 [broker-test.at 30/10/2026](https://www.broker-test.at/?p=37669) |
| **Limite o stop sulle frazioni** | **No.** "Bruchstücke lassen sich weiterhin nur über 'Betrag' zum Marktpreis verkaufen"; "Limit-Käufe und Verkäufe nur für ganze Anteile" | 🟡 [broker-test.at](https://www.broker-test.at/?p=37669), [quantroutine 09/2026](https://quantroutine.com/brokers/trade-republic-fees-explained/), [promarketer](https://www.promarketer.it/investimenti/broker/trade-republic/trade-republic-azioni-frazionate/) |
| Ordini limite o stop sulle **crypto** | Un vecchio articolo del supporto ufficiale (versione Estonia, non più raggiungibile) diceva "Trading is currently not possible using limit or stop orders". Una recensione di settembre 2026 conferma: solo a mercato. Non so se le novità di ottobre 2026 valgano anche per le crypto | 🟡 [snippet support 1492](https://support.traderepublic.com/en-ee/1492-What-are-the-order-types-for-trading-crypto), [quantroutine](https://quantroutine.com/brokers/trade-republic-fees-explained/) / ❌ dopo ottobre 2026 |

### 3.2 Piani di accumulo

| Voce | Valore | Stato |
|---|---|---|
| Costo per esecuzione | **Gratis** ("Esecuzione del piano di accumulo per azioni, ETF o crypto"; nel listino "escluso Investimento Programmato... che sono gratuiti") | ✅ [listino IT v07.2026](https://assets.traderepublic.com/assets/files/further_information_price_list_IT.pdf) |
| Importo per esecuzione | **Da 10 € a 10.000 €** | ✅ listino IT |
| Strumenti | Azioni, ETF, crypto (pagina IT: "piani di accumulo su azioni, ETF o criptovalute") | ✅ [traderepublic.com/it-it](https://traderepublic.com/it-it) |
| ETF UCITS | Sì (TR in Italia vende solo UCITS; quali siano idonei al piano si vede nell'app) | 🟡 |
| **ETP crypto nel piano** | **Non confermato.** I comparatori tedeschi elencano gli ETC sulle materie prime come idonei ai piani; per gli ETP Bitcoin nessuna lista. TR non pubblica un elenco | ❌ [etf.capital](https://etf.capital/10-krypto-etfs-im-vergleich/), [brokerexperte](https://www.brokerexperte.de/etf-sparplaene-traderepublic/) |
| Crypto "vere" nel piano | Sì, circa 50 crypto | ✅ pagina IT crypto |
| Frequenze | Settimanale, due volte al mese, mensile, trimestrale; esecuzioni il 2, 9, 16 o 23 del mese, in orario Xetra | 🟡 [quantroutine 09/2026](https://quantroutine.com/brokers/trade-republic-fees-explained/), [Rankia IT](https://rankia.it/pac-trade-republic/) |
| Vendita delle frazioni del piano | Secondo alcune fonti non sono vendibili lo stesso giorno dell'acquisto | ❌ |

### 3.3 Commissioni (listino ufficiale IT, versione 07.2026)

| Voce | Costo |
|---|---|
| Commissione sull'ordine | gratis |
| **Commissione fissa di regolamento, ordine singolo (Best Price)** | **1,00 €** (con esecuzioni parziali, una volta per giorno di borsa) |
| **Direct Price con scelta della sede** | **2,00 €** |
| Esecuzioni dei piani di accumulo, RoundUp, Saveback, Crypto Spending | gratis |
| Custodia, trasferimento e staking delle crypto | gratis (più le commissioni di rete) |
| Conto titoli, trasferimento titoli in uscita | gratis |
| Dati di mercato L1/L2 | "Specificazione nell'Applicazione". Il comunicato parla di live data gratuiti nell'app e nel Web Terminal; justETF cita feed premium da 5 €/mese per borsa |
| Spread e costi di terzi | **esclusi**: si sommano |

✅ [Listino IT](https://assets.traderepublic.com/assets/files/further_information_price_list_IT.pdf). Il prezzo dell'ordine Direct Price è citato anche dalle 🟡 fonti secondarie.

**Peso sul capitale di 50 €:** un ordine singolo da 50 € costa il 2% per lato (4% andata e ritorno), spread escluso. **I piani di accumulo (gratis, minimo 10 €) sono l'unico modo economico per comprare.** Il motore dovrebbe preferire acquisti tramite piano e usare gli ordini singoli soprattutto per le vendite.

### 3.4 Sedi di esecuzione e orari

| Voce | Valore | Stato |
|---|---|---|
| Best Price (predefinito) | Book aggregato delle borse "rilevanti e liquide", esecuzione **contro Trade Republic** | ✅ comunicato |
| Direct Price | 30 borse a scelta (Xetra, Euronext, Nasdaq, NYSE...); orari della borsa scelta | ✅ comunicato / 🟡 orari ([justETF](https://www.justetf.com/de/academy/trade-republic-news-market-maker.html)) |
| Frazioni e piani dopo luglio 2026 | Una recensione dice "executed via LS Exchange ... with Trade Republic acting as counterparty"; justETF non lo specifica | ❌ |
| Orari Best Price (azioni, ETF, ETP) | Lunedì-venerdì 7:30-23:00 | 🟡 [justETF](https://www.justetf.com/de/academy/trade-republic-news-market-maker.html) |
| Orari crypto | 24/7, anche nei festivi | 🟡 più fonti, tra cui uno snippet del vecchio supporto ufficiale |
| Licenza MTF di TR (gennaio 2026) | Citata da una guida tedesca; applicazione concreta non comunicata | ❌ [rankia.de](https://rankia.de/trade-republic-aktien/) |

### 3.5 Crypto ed ETP: costi e spread

| Voce | Valore | Stato |
|---|---|---|
| Numero di crypto | circa 50, custodite da TR (cold storage), trasferibili verso wallet esterni | ✅ pagina IT crypto |
| Costo per operazione singola | 1 € più spread ("1 € costo di regolamento esterno per operazioni singole") | ✅ pagina IT crypto |
| **Spread BTC** | circa **0,5%** in media (extraETF 2026, Capitalo giugno 2026, finanzwissen luglio 2026); altcoin circa 1,5%. Brokerchooser dice 1%. **TR non pubblica lo spread.** | 🟡 [extraETF](https://extraetf.com/de/krypto-broker/trade-republic-krypto-broker-im-test), [Capitalo](https://www.capitalo.de/anbieter/traderepublic/produkte/krypto), [finanzwissen](https://finanzwissen.de/anbieter/trade-republic/test/crypto/) |
| ETP crypto (ETN/ETC quotati, es. Bitwise `DE000A27Z304`, CoinShares `GB00BLD4ZL17`) | Si negoziano come titoli: 1 € più spread (Best Price) | 🟡 commissione / ❌ **spread degli ETP su TR non misurato da nessuna fonte** |
| Fiscalità | Crypto dirette: 33% (amministrato TR, ✅ pagina IT). ETP crypto: titoli, 26% (vedi `broker-e-fisco.md` §2, 🟡) | ✅ / 🟡 |

**Prezzi osservati oggi su LS-TC (test diretto, solo riferimento):** CSPX circa 715,7 €, XDWD circa 138,6 €, ETN Bitwise BTC circa 59,7 €. Con 50 € **nessuno di questi si compra in quota intera**, quindi niente ordini limite: solo frazioni a mercato o piano di accumulo.

### 3.6 Export delle transazioni per riconciliare il ledger

| Voce | Valore | Stato |
|---|---|---|
| **Export CSV nativo** | Disponibile **dal 15/04/2026** nell'app: *Profilo/Service → Estratti conto (Kontoauszüge) → Export transazioni*. Copre **tutte le registrazioni** di conto titoli e conto liquidità, comprese le transazioni con carta | 🟡 più fonti concordi: [forum Portfolio Performance](https://forum.portfolio-performance.info/t/import-trade-republic-csv-transaktionsexport/39126), [mobiflip 17/04/2026](https://www.mobiflip.de/trade-republic-bekommt-neue-export-funktion-und-outbank-zieht-sofort-nach/), [CoinTracking](https://www.cointracking.info/blog/cointracking-trade-republic-import) |
| Campi | Data e ora, tipo di registrazione, strumento, quantità, prezzo, importo, valuta, `original_amount` e `original_currency`. **Intestazione completa non pubblicata** | 🟡 |
| Problemi noti | Dividendi duplicati ("Cash dividend" più "corrected"); alcune fee (prelievo, ordinazione carta) non riportate bene; staking senza valore; obbligazioni e derivati importati male; su alcune versioni Android serviva un aggiornamento dell'app | 🟡 forum PP |
| Web o solo app | Fonti in conflitto (CoinTracking: solo app mobile) | ❌ |
| PDF | Estratti conto titoli e conto corrente gratuiti (✅ listino). Conferme d'ordine e documenti fiscali in-app (🟡). `pytr` (non ufficiale, vedi rischi in `broker-e-fisco.md` §1.12) li scarica in automatico | ✅ / 🟡 |

**Proposta per il ledger:** import periodico (per esempio settimanale) del CSV caricato a mano dall'utente. Riconciliazione su chiave (data, ISIN o nome, quantità, importo), con regole per scartare i duplicati "corrected" e le righe carta. Le fee vanno dedotte dal listino (1 €, 2 €, 0 € per i piani) e confrontate con il CSV.

---

## 4. Cose da verificare nell'app TR (5 minuti, a mano)

- [ ] Stop-limit e trailing stop sono visibili sul conto italiano? Valgono per gli ETP?
- [ ] Un ETP crypto (es. `DE000A27Z304`) si può mettere in un piano di accumulo?
- [ ] Frequenze del piano disponibili e giorni di esecuzione.
- [ ] Spread mostrato in app su un ETF, un ETP crypto e BTC spot in un orario normale (per esempio alle 15:00): annotarlo per tarare il modello di costo.
- [ ] Il CSV si scarica anche dal Web Terminal o solo dall'app? Copiare l'intestazione delle colonne.
- [ ] Fare una prova del proxy con SPY total return da Alpaca, per misurare la deriva residua del §1.3.
