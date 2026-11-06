# Fonti dati gratuite e hosting a costo zero

> Ricerca del **2026-11-06**. Vincoli: budget 0 €, stack Rust + TypeScript + Python. Mercati: azioni USA, azioni UE/Italia, ETF, crypto.

## Legenda affidabilità

| Etichetta | Significato |
|---|---|
| ✅ **VERIFICATO** | Confermato su una pagina ufficiale del fornitore (URL indicato), letta durante questa ricerca |
| 🟡 **PARZIALE** | Confermato solo da fonti secondarie concordanti, oppure la pagina ufficiale conferma solo una parte del dato |
| ⚠️ **INCERTO / CAMBIATO** | Fonti in conflitto, cambiamento recente o informazione non confermabile |

**Avvertenza generale:** i piani gratuiti cambiano spesso; molte pagine "di confronto" sono marketing di concorrenti. Prima di scrivere codice che dipende da un limite, ricontrollalo sulla pagina ufficiale. Quasi tutti i piani gratuiti sono **solo per uso personale/interno**: va bene per un progetto personale, ma non si possono ridistribuire i dati (per esempio mostrandoli su una webapp pubblica).

---

## 1. Prezzi (storico giornaliero, intraday, realtime/ritardati)

### 1.1 Azioni USA ed ETF USA

| Fonte | Rate limit (free) | Ritardo / realtime | Storico | Licenza / ToS | Stato |
|---|---|---|---|---|---|
| **Alpaca Market Data (Basic)** | 200 chiamate/min allo storico; WebSocket fino a 30 simboli azionari | Realtime solo feed **IEX** (circa 2–3% del volume USA). I dati di tutte le borse (SIP) via storico non coprono gli **ultimi 15 minuti** | Azioni dal 2016; intraday a minuto incluso | Piano Basic gratuito, predefinito sia per gli account paper sia per quelli live. Il SIP realtime richiede Algo Trader Plus a 99 $/mese. I dati crypto storici non richiedono autenticazione | ✅ [docs.alpaca.markets](https://docs.alpaca.markets/docs/about-market-data-api) · ⚠️ apertura dell'account a residenti in Italia/UE non verificata |
| **Massive (ex Polygon.io), Stocks Basic** | 5 chiamate/min (HTTP 429 oltre il limite) | Solo end-of-day: le barre di un giorno sono disponibili dopo la mezzanotte ET | 2 anni | Gratis senza scadenza. Rebrand Polygon→Massive: `api.polygon.io` e `api.massive.com` restano entrambi attivi con le stesse chiavi | ✅ [KB limiti](https://massive.com/knowledge-base/article/what-is-the-request-limit-for-massives-restful-apis), [KB EOD](https://massive.com/knowledge-base/article/on-the-free-basic-plan-when-can-i-pull-the-previous-trading-days-data) · la pagina /pricing non mostra più il piano gratuito ⚠️ |
| **Tiingo (Starter)** | 50 richieste/ora, 1.000/giorno, 500 simboli unici al mese, 1 GB/mese di banda | EOD, più IEX intraday (inclusione nel free non chiarita dalla pagina) | Prezzi: oltre 30 anni; fondamentali: 5 anni | "Internal use": solo uso personale, nessuna esposizione a terzi | ✅ [tiingo.com/about/pricing](https://www.tiingo.com/about/pricing) |
| **Alpha Vantage** | **25 richieste/giorno** (il limite al minuto non è indicato sulla pagina ufficiale) | I dati realtime e ritardati di 15 minuti per gli USA sono **premium** | Daily con storico lungo (dato dalla documentazione, non riverificato) | Accesso esteso solo per progetti open source o educativi verificati | ✅ [alphavantage.co/support](https://www.alphavantage.co/support/) |
| **Finnhub (free)** | ~60 chiamate/min più un tetto globale di 30/s | Quote USA (realtime o ritardate: le fonti sono in conflitto); WebSocket base | Le candele storiche sono state rese premium in passato (non riverificato) | Uso commerciale limitato sul piano free | ⚠️ le pagine ufficiali sono renderizzate in JS e non le ho potute leggere; dati da [fonti secondarie](https://raw.githubusercontent.com/api-evangelist/finnhub/refs/heads/main/rate-limits/finnhub-rate-limits.yml) |
| **Twelve Data (Basic)** | 8 crediti/min, 800 crediti/giorno (il costo in crediti varia per endpoint) | Free: USA, forex e crypto. **Borse non USA a pagamento** | n/d | Solo uso interno | ✅ limiti: [support.twelvedata.com](https://support.twelvedata.com/en/articles/5194820-api-credits-limits) · 🟡 copertura solo USA ([pricing](https://twelvedata.com/pricing.md)) |
| **Financial Modeling Prep (Basic)** | 250 chiamate/giorno, 500 MB di banda su 30 giorni mobili | EOD | Storico EOD; oltre 150 endpoint | ⚠️ una fonte terza parla di "non-commercial only", non confermato da FMP | ✅ [FMP help](https://site.financialmodelingprep.com/insights/platform/what-happens-when-you-hit-your-fmp-api-limit) |
| **EODHD (free)** | **20 chiamate/giorno** (più 500 chiamate di benvenuto una tantum) | Solo EOD | **1 anno** | Alcuni tipi di dato sono esclusi dal free | ✅ [eodhd.com](https://eodhd.com/financial-apis/api-for-historical-data-and-volumes) |
| **yfinance (Yahoo, non ufficiale)** | Nessun limite pubblicato; frequenti blocchi per IP (`YFRateLimitError`) | Quote ritardate o quasi realtime a seconda della borsa; intraday a 1 minuto solo per gli ultimi ~7 giorni (dato noto dalla libreria, non riverificato) | Daily lungo | Il README di yfinance indica "personal use only". I ToS di Yahoo vietano l'accesso automatizzato non fornito da Yahoo. **Rischio legale e operativo** | 🟡 [issue #2431](https://github.com/ranaroussi/yfinance/discussions/2431), [#2480](https://github.com/ranaroussi/yfinance/issues/2480) |
| **Stooq** | Quota giornaliera non dichiarata ("Exceeded the daily hits limit") | EOD | Lungo (decenni) | ⚠️ **Cambiato nel 2026**: serve una API key ottenuta tramite CAPTCHA; i download bulk richiedono CAPTCHA manuale | ⚠️ solo [fonti secondarie](https://providers.apievangelist.com/providers/stooq/) e [forum utenti](https://www.fundmanagersoftware.com/forum/viewtopic.php?p=28804) |

### 1.2 Azioni UE / Borsa Italiana (Euronext Milan) ed ETF UCITS

| Fonte | Note | Stato |
|---|---|---|
| **yfinance (suffisso `.MI`, `.DE`, `.PA`, `.AS`…)** | Copertura ampia e gratuita, ma con gli stessi rischi legali e di blocco visti sopra | 🟡 |
| **EODHD free** | Copre le borse UE ma solo 20 chiamate/giorno e 1 anno di storico: utile solo per verifiche a campione | ✅ (limiti) |
| **Stooq** | Storicamente copriva molte borse UE; ora con API key e CAPTCHA | ⚠️ |
| **Twelve Data** | Le borse UE sono a pagamento | 🟡 |
| **Alpaca / Massive / Tiingo** | Solo USA | ✅ |
| **Borsa Italiana (sito)** | Le quote sul sito sono ritardate di 15 minuti; nessuna API pubblica gratuita trovata. Lo scraping è sconsigliato | ⚠️ |

> **Conclusione UE/IT:** **non esiste una fonte gratuita, ufficiale e affidabile** per lo storico e l'intraday di Borsa Italiana. Realisticamente servono yfinance o Stooq per lo storico EOD (accettando il rischio), più la cache locale come fonte di verità. Se il broker scelto offre dati via API (per esempio IBKR, che però ha costi di abbonamento ai dati), quella diventa la fonte primaria per l'esecuzione.

### 1.3 Crypto

| Fonte | Rate limit | Storico | ToS | Stato |
|---|---|---|---|---|
| **Binance Spot API (pubblica)** | 6.000 di request weight al minuto per IP (HTTP 429 oltre il limite). Endpoint solo-dati su `data-api.binance.vision` senza chiave | Klines via API | Dati pubblici | ✅ [rate limits](https://developers.binance.com/docs/binance-spot-api-docs/web-socket-api/rate-limits), [market data only](https://developers.binance.com/docs/binance-spot-api-docs/faqs/market_data_only) |
| **Binance Data Collection (`data.binance.vision`)** | File statici, nessun limite pubblicato | **File giornalieri e mensili di klines e trade**, ideali per il backtest | Pubblico | ✅ [github.com/binance/binance-public-data](https://github.com/binance/binance-public-data/) · ⚠️ l'accesso da alcune giurisdizioni può essere limitato |
| **Kraken REST (pubblica)** | Circa 1 richiesta/s per IP consigliata | OHLC: **solo le ultime 720 candele** (a 1 minuto = 12 ore). Per lo storico profondo serve l'endpoint Trades (1.000 trade per chiamata). Nessun dump bulk | Pubblico | ✅ [docs.kraken.com](https://docs.kraken.com/exchange/guides/general/historical-data) |
| **CoinGecko Demo** | 10.000 crediti/mese; rate **30/min** secondo una fonte, **100/min** secondo la pagina di pricing letta | Daily e orario: 1 anno; a 5 minuti: 1 giorno | **Attribuzione obbligatoria**; piano "per test ed esplorazione" | ✅ [coingecko.com/en/api/pricing](https://www.coingecko.com/en/api/pricing) · ⚠️ rate/minuto in conflitto |
| **CCXT** (libreria open source MIT, Python/TS) | Eredita i limiti di ciascun exchange (`enableRateLimit`) | Dipende dall'exchange | Libreria open source | 🟡 da conoscenza generale, non riverificato oggi |

---

## 2. Fondamentali e calendari degli utili

| Fonte | Cosa offre gratis | Limiti | Stato |
|---|---|---|---|
| **SEC EDGAR, XBRL API (`data.sec.gov`)** | `companyfacts`, `companyconcept`, `frames` (fondamentali dichiarati in 10-K e 10-Q) e `submissions` (tutti i filing per CIK) in JSON | **10 richieste/s**, User-Agent con contatto **obbligatorio**. Gratuito e di pubblico dominio | ✅ [sec.gov Accessing EDGAR Data](https://www.sec.gov/os/accessing-edgar-data) |
| **FMP Basic** | Profili, financial statements ed earnings calendar (endpoint inclusi nei 250/giorno; la disponibilità per singolo endpoint va verificata) | 250/giorno | 🟡 |
| **Finnhub free** | Basic financials, earnings calendar e company news sono storicamente gratuiti | ~60/min | ⚠️ non verificato sulla pagina ufficiale |
| **Alpha Vantage** | `OVERVIEW`, `EARNINGS`, `EARNINGS_CALENDAR` | 25/giorno, quindi inutilizzabile su un universo ampio | 🟡 |
| **Tiingo** | Fondamentali con 5 anni di storico | 50/h | ✅ (storico 5 anni) |
| **UE/Italia** | Nessuna API XBRL ufficiale equivalente a EDGAR trovata. Bilanci e comunicati vanno presi dai siti degli emittenti o da Borsa Italiana | — | ⚠️ |

---

## 3. "Smart money"

| Fonte | Dettagli | Ritardo intrinseco | Stato |
|---|---|---|---|
| **13F (SEC)** | Via EDGAR API (filing `13F-HR`) oppure **Form 13F Data Sets** trimestrali in zip (DERA) | Deposito entro 45 giorni dalla fine del trimestre (regola nota). I dataset si aggiornano ogni 3 mesi | ✅ [Form 13F data sets](https://catalog.data.gov/dataset/form-13f-data-sets), [EDGAR](https://www.sec.gov/os/accessing-edgar-data) |
| **Form 3/4/5 (insider)** | **Insider Transactions Data Sets** (dal 2006, XML normalizzato, aggiornamento trimestrale). Per il quasi-tempo-reale serve il polling EDGAR dei Form 4 | Il Form 4 va depositato entro 2 giorni lavorativi (regola nota). Il dataset trimestrale è più lento | ✅ [sec.gov/dera/data/form-345](https://www.sec.gov/dera/data/form-345) |
| **Congresso USA, fonti primarie** | Senato: eFD (`efdsearch.senate.gov`). Camera: Clerk (`disclosures-clerk.house.gov`, PTR in PDF, indice annuale scaricabile: dato noto, non riverificato) | PTR entro 30 giorni dalla notifica e **mai oltre 45 giorni** dalla transazione. Gli importi sono in fasce | ✅ regola: [Senate Ethics PDF](https://www.ethics.senate.gov/public/_cache/files/3feffe08-91b6-487f-9074-8e188cb0af62/periodic-transaction-requirements.pdf) · ⚠️ i PDF della Camera sono spesso scansioni, quindi serve OCR |
| **House/Senate Stock Watcher** | Dataset open source storici | Lo stato attuale (attivo o abbandonato) non è confermato | ⚠️ |
| **Quiver Quantitative** | Sito: dati sul Congresso consultabili gratis. **API a pagamento** (circa 10 $/mese "Hobbyist", secondo fonti terze) | — | ⚠️ [findmymoat](https://www.findmymoat.com/vs/options-profit-calculator-vs-quiver-quantitative): nessuna API gratuita trovata |
| **Capitol Trades** | Consultazione web gratuita; **nessuna API ufficiale** trovata; ToS sullo scraping non reperiti | — | ⚠️ |
| **Unusual Whales** | API solo sui piani a pagamento (circa 50 $/mese) | — | 🟡 [unusualwhales.com](https://unusualwhales.com/guides/best-congressional-trading-trackers) |
| **FMP Senate/House endpoints** | `/stable/senate-latest`, `/stable/house-latest` | Inclusione nel piano free non confermata | 🟡 [FMP docs](https://site.financialmodelingprep.com/developer/docs/senate-disclosure-api) |
| **Consob, partecipazioni rilevanti (art. 120 TUF)** | Pagine web consultabili per emittente; **nessun open data o API bulk trovato**. Consob stessa avvisa che la sezione è "in aggiornamento" | Comunicazioni entro pochi giorni dal superamento soglia | ⚠️ [consob.it](https://www.consob.it/web/consob/home-page-en): serve scraping, verificando le condizioni d'uso |
| **Short interest USA (FINRA)** | Tutti i titoli **quotati e OTC**, due volte al mese, pubblicati il 7° giorno lavorativo dopo la data di regolamento. API "Equity" con 5 anni mobili | Circa 2 settimane | ✅ [finra.org](https://www.finra.org/finra-data/browse-catalog/equity-short-interest): uso **non commerciale** |
| **Short UE/Italia** | Posizioni nette corte ≥0,5% pubblicate da Consob/ESMA (obbligo SSR, regola nota) | — | ⚠️ formato e endpoint non verificati |

---

## 4. Sentiment e notizie

| Fonte | Limiti free | ToS / note | Stato |
|---|---|---|---|
| **Finnhub company/market news** | Inclusa nei ~60/min | Endpoint free secondo fonti secondarie | ⚠️ |
| **Marketaux** | **100 richieste/giorno**, **3 articoli per richiesta**; sentiment per entità da -1 a 1 | Lo storico profondo e i filtri avanzati sono a pagamento | ✅ [marketaux.com/pricing](https://marketaux.com/pricing) |
| **NewsAPI.org (Developer)** | 100 richieste/giorno, **articoli ritardati di 24 h**, ricerca fino a 1 mese | **Vietato in produzione e staging**, anche per uso interno: inadatto | ✅ [newsapi.org/pricing](https://newsapi.org/pricing) |
| **GDELT DOC 2.0** | Gratis senza chiave; nessuna quota formale ma limitazione attiva, indicativamente 1 richiesta ogni 5 s | Ricerca dal 1/1/2017; i modi non-timeline coprono solo gli ultimi 3 mesi della finestra | 🟡 [blog GDELT](https://blog.gdeltproject.org/doc-2-0-updates-1-5-year-searching-and-updated-mobile-interface/) |
| **Reuters RSS** | **Chiusi da giugno 2020**. Alternativa: RSS di Google News con `site:reuters.com` | Reuters blocca molti bot | ✅ chiusura: [feeder.co](https://feeder.co/knowledge-base/rss-content/reuters-rss-feeds/) |
| **Il Sole 24 Ore RSS** | Per esempio `ilsole24ore.com/rss/finanza.xml`, `/rss/economia.xml` | Uso personale; da verificare le condizioni | 🟡 [feedspot](https://rss.feedspot.com/ilsole24ore_rss_feeds/) |
| **Reddit API** | ~100 QPM per client OAuth (uso non commerciale). **Da novembre 2025 "Responsible Builder Policy": il self-service è chiuso e i nuovi accessi richiedono approvazione.** Il commerciale è a pagamento (0,24 $/1.000 chiamate nell'annuncio 2023) | PRAW funziona solo con credenziali approvate. Alcune fonti indicano ulteriori scadenze a fine 2026–2027 (non confermate) | ⚠️ [r/redditdev (mirror)](https://r.datuan.dev/r/redditdev/comments/1oug31u/introducing_the_responsible_builder_policy_new/noh6fun), [dev.to](https://dev.to/agenthustler/reddit-data-api-2026-after-the-pricing-change-heres-what-developers-actually-use-4o2h) |
| **StockTwits** | API ufficiale con accessi ristretti o su approvazione; posting rimosso nel 2024 | Stato registrazioni 2026 non confermato | ⚠️ |
| **X / Twitter** | **Nessun tier gratuito in lettura** per i nuovi sviluppatori. Dal 6/2/2026 il modello è pay-per-use (circa 0,005 $ per post letto, cifre in conflitto); Basic chiuso alle nuove iscrizioni | Fuori budget | ⚠️ [postproxy](https://www.postproxy.dev/blog/x-api-pricing-2026/), [opentweet](https://opentweet.io/x-api-pricing) |
| **Google Trends** | **pytrends archiviato il 17/4/2025**, parzialmente funzionante e soggetto a HTTP 429. **API ufficiale Google Trends in alpha** (dal 24/7/2025) con accesso su candidatura | Usare cache aggressiva e poche keyword | 🟡 [dev.to](https://dev.to/rimulabs/pytrends-is-archived-how-to-migrate-your-google-trends-code-no-more-429s-4e63) |
| **CNN Fear & Greed** | Nessuna API ufficiale. Endpoint non documentato `production.dataviz.cnn.io/index/fearandgreed/graphdata/` usato dalla community | Può cambiare senza preavviso | ⚠️ |
| **Crypto Fear & Greed (alternative.me)** | `api.alternative.me/fng/?limit=0` restituisce tutto lo storico; senza chiave | **Uso commerciale consentito con attribuzione** accanto al dato | ✅ [alternative.me](https://alternative.me/crypto/fear-and-greed-index/) |
| **Put/Call ratio (Cboe)** | I CSV gratuiti sono **fermi al 4/10/2019**. Da allora solo pagina web giornaliera (`cboe.com/us/options/market_statistics/daily/`) | Per lo storico serve scraping giorno per giorno; dati completi a pagamento su DataShop | ✅ [cboe.com historical](https://cboe.com/us/options/market_statistics/historical_data/) |

---

## 5. Macro

| Fonte | Accesso | Limiti | Licenza | Stato |
|---|---|---|---|---|
| **FRED (St. Louis Fed)** | API REST con chiave gratuita | 120 richieste/min per chiave (HTTP 429) | Attribuzione; alcune serie hanno copyright del fornitore originale | 🟡 limiti da fonti secondarie concordanti |
| **ECB Data Portal** | SDMX 2.1 REST su `data-api.ecb.europa.eu/service`, CSV/JSON/XML, senza chiave. I vecchi endpoint SDW sono stati reindirizzati solo fino all'**1/10/2025** | Nessun limite pubblicato | Riuso consentito con "Source: ECB statistics" (fonte secondaria) | ✅ API: [data.ecb.europa.eu/help/api](https://data.ecb.europa.eu/help/api) · 🟡 licenza |
| **Eurostat** | `ec.europa.eu/eurostat/api/dissemination`: JSON-stat 2.0, SDMX 2.1/3.0, senza chiave | Le richieste grandi conviene farle in modo asincrono | Gratuito | ✅ [Eurostat API getting started](https://ec.europa.eu/eurostat/web/user-guides/data-browser/api-data-access/api-getting-started) |

---

## 6. Hosting gratuito per un sistema sempre acceso

| Servizio | Risorse free | Rust 24/7? | Python + ML leggero? | Sleep / inattività | Stato |
|---|---|---|---|---|---|
| **Oracle Cloud Always Free (Ampere A1)** | ⚠️ **Ridotto**: la documentazione ufficiale ora indica **1.500 OCPU-ore e 9.000 GB-ore al mese, cioè 2 OCPU e 12 GB** (non più 4 OCPU e 24 GB). Inoltre 200 GB di block storage e 10 TB/mese di traffico in uscita | **Sì** (VM completa) | **Sì** (12 GB bastano per scikit-learn, LightGBM, piccoli PyTorch su CPU) | **Recupero delle istanze inattive**: su 7 giorni, se CPU p95, rete e memoria restano tutte sotto il 20% l'istanza può essere recuperata. Disponibilità di capacità ARM spesso scarsa | ✅ [docs.oracle.com](https://docs.oracle.com/en-us/iaas/Content/FreeTier/resourceref.htm) · taglio riportato da [InfoQ 07/2026](https://infoq.com/news/2026/07/oracle-cloud-free-tier-limits/) |
| **Google Cloud e2-micro** | 1 e2-micro non preemptible al mese in us-west1, us-central1 o us-east1; 30 GB di disco standard; 1 GB/mese di traffico in uscita dal Nord America | **Sì** (VM, ma circa 1 GB di RAM) | Solo molto leggero (inferenza piccola); niente training | Nessuno sleep. Modifiche con 30 giorni di preavviso | ✅ [docs.cloud.google.com free](https://docs.cloud.google.com/free/docs/free-cloud-features) |
| **Google Cloud Run** | 2 M richieste/mese, 180.000 vCPU-s e 360.000 GB-s | No (request-driven) | Job brevi | Scala a zero | ✅ stessa pagina |
| **Fly.io** | **Nessun piano free per i nuovi account** (da ottobre 2024): solo trial, poi pay-as-you-go | No a costo zero | No | — | 🟡 [flaviocopes 09/2026](https://flaviocopes.com/hosting-free-tiers.md) |
| **Render (Free)** | 750 ore di istanza al mese per workspace | **No**: il web service si spegne dopo **15 minuti senza traffico in ingresso** (riavvio in circa 1 minuto). **I background worker non sono disponibili nel free** | Solo come web API dormiente | Sì | ✅ [render.com/docs/free](https://render.com/docs/free) |
| **Railway** | Trial con 5 $ una tantum (30 giorni), poi piano Free con **1 $ di credito al mese**, 0,5 GB di RAM per servizio | Non realisticamente 24/7 con 1 $/mese | No | Servizi in pausa a credito esaurito | ✅ [docs.railway.com](https://docs.railway.com/pricing/free-trial) |
| **Cloudflare Workers (Free)** | 100.000 richieste/giorno (reset a mezzanotte UTC), **10 ms di CPU per richiesta e per Cron Trigger** (le attese di rete non contano). KV: 100.000 letture e 1.000 scritture al giorno | No (Rust via WASM sì, ma non come processo persistente) | No | Event-driven | ✅ [limits](https://developers.cloudflare.com/workers/platform/limits) |
| **Cloudflare D1 (Free)** | 10 DB, 500 MB per DB, 5 GB totali; 100.000 query/giorno (fonte secondaria) | — | — | — | ✅ [D1 limits](https://developers.cloudflare.com/d1/platform/limits/) |
| **Vercel Hobby** | Cron **al massimo 1 volta al giorno**, con precisione all'ora | No | No | Serverless | ✅ [vercel cron pricing](https://vercel.com/docs/cron-jobs/usage-and-pricing) · ⚠️ uso non commerciale (non riverificato) |
| **Supabase Free** | 2 progetti, 500 MB di DB, 1 GB di file storage | — | — | **Progetto in pausa dopo 1 settimana di inattività** (ripristino manuale) | 🟡 [supabase pricing](https://Supabase.io/pricing) |
| **Neon Free** | 100 progetti, 100 CU-ore per progetto al mese, **1 GB per progetto** (20 GB totali), 5 GB di traffico | — | — | Scala a zero (gratuito solo se scala a zero); oltre 1 GB le scritture falliscono | ✅ [neon.com FAQ (01/10/2026)](https://neon.com/faqs/free-plan-limits-and-quotas) |
| **GitHub Actions (cron)** | Gratis sui repo pubblici. Minuti limitati sui privati (quota non riverificata) | No (job limitati a qualche ora) | Sì, per job batch (backtest, retrain, ingest EOD) | Intervallo minimo **5 minuti**; **ritardi o job saltati nei momenti di carico** (inizio di ogni ora); **cron disabilitato dopo 60 giorni senza attività** nei repo pubblici | ✅ [docs.github.com](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows) |

**Sintesi hosting:** l'unica opzione free capace di far girare **Rust 24/7 + Python con ML** è **Oracle A1** (ora 2 OCPU e 12 GB). Il fallback è **GCP e2-micro** (solo Rust leggero). Gli altri servizi vanno usati come complementi: scheduler, frontend, DB gestito.

---

## 7. Architettura dati consigliata (costo zero)

```
                    ┌──────────────────────── Oracle Cloud A1 (2 OCPU / 12 GB, Always Free) ───────────────────────┐
  Alpaca IEX WS ───►│  [Rust] engine: ingest realtime, risk, execution (Alpaca paper → live)                        │
  Binance/Kraken WS►│        │ scrive tick/barre                                                                   │
                    │        ▼                                                                                     │
                    │  PostgreSQL (+ TimescaleDB) locale  ◄── [Python] job: EOD, fondamentali, 13F/Form4, macro,   │
                    │  + Parquet/DuckDB per lo storico     │   news/sentiment, feature, training ML leggero        │
                    │        │                                                                                     │
                    │  [TS] API (Fastify/Hono) + orchestratore (cron interni)                                      │
                    └────────┼─────────────────────────────────────────────────────────────────────────────────────┘
                             │ HTTPS (Cloudflare Tunnel)
                ┌────────────┴───────────┐
                ▼                        ▼
   Cloudflare Pages/Workers         GitHub Actions (repo privato o pubblico)
   webapp TS + proxy/auth           - cron di backup (heartbeat/watchdog verso la VM)
                                    - backtest/retrain pesanti a richiesta
                                    - backup notturni (pg_dump/Parquet) come artifact o release
```

**Scelte e motivazioni**

1. **Fonte di verità = cache locale.** Ogni dato scaricato va salvato in Parquet (storico) e Postgres (stato e ultimi giorni). Con limiti come 25 o 250 chiamate al giorno, la strategia vincente è un **ingest incrementale** con riempimento progressivo dei buchi.
2. **Prezzi USA:** Alpaca Basic (IEX realtime, storico dal 2016 a 200/min) come fonte primaria; Tiingo per lo storico EOD lungo e aggiustato (50/h, 500 simboli al mese); Massive come controllo incrociato EOD.
3. **Prezzi UE/IT ed ETF UCITS:** yfinance `.MI` per l'EOD con rate limit molto prudente (per esempio 1 richiesta ogni 2–5 s, una sola passata serale), con Stooq (API key) come seconda fonte. **Rischio ToS documentato**: per l'operatività reale serve il feed del broker.
4. **Crypto:** dump `data.binance.vision` per lo storico più WebSocket pubblici Binance/Kraken per il realtime, tramite crate Rust o CCXT (Python/TS) per il resto.
5. **Fondamentali e smart money:** SEC EDGAR (gratuito, 10 req/s, User-Agent obbligatorio) per XBRL, 13F e Form 4; FINRA per lo short interest; fonti primarie House/Senate per il Congresso (PDF più OCR); Consob via scraping leggero.
6. **Sentiment:** GDELT (gratis), Marketaux (100/giorno), RSS (Sole 24 Ore, Google News `site:reuters.com`), alternative.me per il F&G crypto. **Esclusi**: X (a pagamento), NewsAPI (vietato in produzione); Reddit solo se l'accesso viene approvato.
7. **Macro:** FRED + ECB Data Portal + Eurostat, aggiornati una volta al giorno o alla settimana.
8. **Mitigazione rischi Oracle:** il carico reale (ingest, feature, ML) tiene la VM sopra la soglia di inattività. Backup giornalieri fuori dalla VM. Infrastructure as code (cloud-init/Ansible) per ricreare tutto in meno di un'ora su GCP e2-micro o su un PC di casa.
9. **DB gestito (opzionale):** Neon free (1 GB per progetto, scala a zero) per i dati che la webapp deve leggere senza passare dalla VM. Supabase solo se si accetta la pausa dopo 7 giorni.

---

## 8. Riepilogo: cose cambiate di recente o incerte

| Tema | Cosa | Fonte |
|---|---|---|
| Oracle A1 | **Da 4 OCPU/24 GB a 2 OCPU/12 GB** (doc ufficiale; taglio riportato a metà 2026) | [docs.oracle.com](https://docs.oracle.com/en-us/iaas/Content/FreeTier/resourceref.htm) |
| Polygon → Massive | Rebrand; free invariato (5/min, EOD, 2 anni) | [massive KB](https://massive.com/knowledge-base/article/what-is-the-request-limit-for-massives-restful-apis) |
| Stooq | API key con CAPTCHA (2026) | fonti secondarie |
| Reddit | Self-service chiuso (novembre 2025) | r/redditdev |
| X | Pay-per-use dal 6/2/2026, nessun free in lettura | blog terzi |
| pytrends | Archiviato (aprile 2025); API Trends ufficiale in alpha | dev.to |
| ECB | Endpoint SDW dismessi (redirect fino all'1/10/2025) | [data.ecb.europa.eu](https://data.ecb.europa.eu/help/api) |
| Neon | Free a 1 GB per progetto (prima 0,5 GB) | [neon.com](https://neon.com/faqs/free-plan-limits-and-quotas) |
| Fly.io | Nessun free per i nuovi account | fonti terze |
| Incerti | Limiti ed endpoint free di Finnhub; rate/minuto di CoinGecko (30 o 100); stato di Capitol Trades, Quiver, StockTwits e Stock Watcher; apertura conto Alpaca dall'Italia; licenza "non-commercial" di FMP | — |
