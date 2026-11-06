# Top player, evidenza sulla replica e soluzioni esistenti

> Ricerca del 2026-11-06. Contesto: capitale 50 €, budget 0 €, mercati azioni USA/UE, ETF, crypto. Stack: Rust + TypeScript + Python.
>
> **Legenda affidabilità**
> - **[V]** verificato: fonte primaria (lettera agli azionisti, abstract del paper, documento ufficiale, API GitHub) letta o citata con URL.
> - **[S]** fonte secondaria coerente (stampa finanziaria, riassunti di terzi), non verificata sulla fonte primaria.
> - **[I]** incerto: fonti in conflitto, datate o non trovate. Non usare come dato di progetto senza un nuovo controllo.

---

## 0. TL;DR

1. **Copiare chi è osservabile e lento, non chi è veloce.** Buffett/Berkshire, Li Lu, Klarman, Ackman, Tepper e Druckenmiller pubblicano i 13F (ritardo fino a 45 giorni dopo la fine del trimestre). Renaissance (Medallion) e qualsiasi HFT non si possono replicare.
2. **L'evidenza accademica è mista.** Il clone di Berkshire ha generato alfa storico [V/S], gli acquisti "opportunistici" e in cluster degli insider hanno alfa documentato [V], i trade del Congresso nel complesso **no** (con l'eccezione dei leader [V]), il copy trading **aumenta il rischio** [V].
3. **Dati primari gratis:** SEC EDGAR (13F, Form 4) senza chiave API, 10 richieste/s [V]. Tutto il resto (Dataroma, WhaleWisdom, Quiver, Capitol Trades) è un'interfaccia su questi dati pubblici.
4. **Framework base consigliato:** NautilusTrader (core in Rust, Python sopra, adapter IBKR e Binance/Kraken/Bybit) [V], con ccxt per la crypto in TS/Python ed edgartools per l'ingestion SEC. Per la parte azioni USA "lenta" non serve un motore HFT: basta uno script di ribilanciamento.
5. **Con 50 € il vincolo vero sono i costi**: servono frazionamento e zero commissioni. Qualsiasi commissione fissa di circa 1 € per ordine si mangia più del 2% del capitale a ogni trade.

---

## 1. Top investitori: track record e osservabilità

### 1.1 Tabella principale

| Gestore / veicolo | Stile | Rendimento documentato | Affid. | Mosse osservabili | Ritardo | Replicabile? |
|---|---|---|---|---|---|---|
| **Warren Buffett / Berkshire Hathaway** (dal 2026 CEO Greg Abel) | Value, concentrato, holding lunghissimo | Valore di mercato per azione: **+19,7%/anno 1965-2025 contro +10,5% dell'S&P 500** con dividendi. Nel 2025: +10,9% contro +17,9% dell'S&P | [V] lettera 2025 (riportata da più fonti) | 13F trimestrale, lettera annuale, 13D/Form 4 sopra il 10% | 13F fino a 45 gg dopo la fine del trimestre; Berkshire ottiene a volte un **trattamento confidenziale** e ritarda alcune posizioni | **Sì** (bassa rotazione). Attenzione: dal 2026 le decisioni non sono più di Buffett |
| **Jim Simons / Renaissance Medallion** | Quant, statistico, alta frequenza, leva | 1988-2018: **~66%/anno lordo, ~39% netto** (medie aritmetiche, da Zuckerman, *The Man Who Solved the Market*). CAGR lordo stimato 63,3% | [S] | Il 13F di Renaissance riflette soprattutto i fondi aperti al pubblico (RIEF/RIDA), **non Medallion**. Medallion è chiuso agli esterni. Simons è morto nel 2024 | 13F inutile: rotazione di giorni od ore | **No** |
| **Stanley Druckenmiller / Duquesne** | Macro discrezionale, concentrato, usa anche derivati e valute | **~30%/anno 1981-2010** (o 1986-2010 secondo alcune fonti). Il "nessun anno in perdita" è contestato per il 2010 | [S] | Family office dal 2010. Il 13F mostra solo le azioni USA long, non macro, FX, bond o short | 45 gg + forte rotazione | **Parziale e debole**: il 13F è una fetta piccola della strategia |
| **Bill Ackman / Pershing Square** | Attivista, molto concentrato (8-12 titoli) | PSLP dal 2004: **15,9% CAGR contro 10,7% dell'S&P**. PSH (dal 2012): **12,9% contro 14,9% dell'S&P**, quindi sottoperforma. 2025: +20,9% contro +17,9% | [V] Annual Report 2025 PSH | 13F, lettere, **NAV settimanale PSH**, 13D | 13D entro 10 gg dal superamento del 5% (più tempestivo del 13F) | **Sì** (pochi titoli, lenti). In alternativa si può comprare direttamente PSH (Euronext Amsterdam/LSE) |
| **David Tepper / Appaloosa** | Distressed, macro, azioni | **~25-28% netto/anno dal 1993** (le fonti divergono); lordo >28-36% | [S]/[I] | 13F (dal 2019 solo capitale personale) | 45 gg | Parziale: la componente distressed e credito non compare nel 13F |
| **Li Lu / Himalaya Capital** | Value concentrato (scuola Munger), Asia + USA | **26,4%/anno dal 1998** (dato 2010); altre fonti dicono ~30% | [S]/[I]: nessun dato auditato pubblico | 13F: poche posizioni USA. Le posizioni asiatiche, come BYD, non compaiono | 45 gg | Sì per la parte USA, che però è incompleta |
| **Seth Klarman / Baupost** | Value profondo, molta liquidità, credito e private | **~19%/anno netto dal 1982/83 a circa il 2009-2010**; rendimenti molto peggiori dopo il 2014 | [S] (Bloomberg 2010) | 13F: piccola parte del patrimonio | 45 gg | Debole: la maggior parte non è azionario quotato |
| **Terry Smith / Fundsmith Equity** (UE/UK) | Quality growth, buy and hold | Dal lancio (nov. 2010) ~**12,9-14,8%/anno** secondo la data di cut-off. **5 anni consecutivi sotto l'MSCI World**; 2025: **+0,8% contro +12,8%** | [S] (AJ Bell, IFA Magazine) | Factsheet mensile (top 10), lettera annuale con lista completa | Mensile | **Sì** (portafoglio stabile di circa 25-30 titoli), ma il momento attuale è debole |
| **Michael Burry / Scion** | Contrarian, concentrato, usa opzioni | Nessuna serie pubblica affidabile | [I] | **Registrazione SEC terminata il 10/11/2025: niente più 13F.** Ultimo 13F per il terzo trimestre 2025 | n/a | **Non più osservabile** |

Fonti principali:
- Berkshire 2025: <https://www.nbcdfw.com/news/business/money-report/warren-buffetts-return-tally-after-60-years-5502284/3832965/>, <https://www.pulse.bot/wealth-management/news/berkshire-hathaway-2025-annual-shareholder-letter-by-greg-abel-45b09421-f006-4d67-8e49-f55eec2b08f7/>. Primaria: <https://www.berkshirehathaway.com/letters/letters.html>
- Medallion: <https://ritholtz.com/2019/10/bbrg-how-jim-simons-built-the-best-hedge-fund-ever>, <https://www.cxoadvisory.com/investing-expertise/proof-of-superior-investment-expertise/>
- Druckenmiller: <https://en.wikipedia.org/wiki/Stanley_Druckenmiller>, <https://newsletter.finchat.io/p/stan-druckenmiller-30-returns-30-years>
- Pershing Square: <https://assets.pershingsquareholdings.com/wp-content/uploads/2026/02/18175039/Pershing-Square-Holdings-Ltd.-2025-Annual-Report.pdf>
- Tepper: <https://moneyweek.com/468619/the-worlds-greatest-investors-david-tepper>, <https://hedgefundalpha.com/news/appaloosa-management-returns-money-clients/>
- Li Lu: <https://en.wikipedia.org/wiki/Himalaya_Capital>, <https://quartr.com/insights/investment-strategy/li-lu-the-man-who-impressed-charlie-munger>
- Klarman: <https://www.bloomberg.com/news/articles/2010-06-17/the-financial-life-seth-klarman>
- Fundsmith: <https://www.ajbell.co.uk/group/news/fundsmith-underperforms-fifth-calendar-year-row>, <https://ifamagazine.com/fundsmith-underperforms-for-the-fifth-calendar-year-in-a-row/>
- Burry: <https://benzinga.com/markets/hedge-funds/25/11/48827238/big-short-michael-burry-de-registers-his-hedge-fund-scion-asset-management>

### 1.2 Tempi delle fonti pubbliche (USA)

| Documento | Chi lo deposita | Contenuto | Scadenza | Note |
|---|---|---|---|---|
| **Form 13F** | Gestori istituzionali con più di 100 M$ in titoli 13(f) | Solo posizioni **long** in azioni USA, ETF e opzioni (non i nozionali) | Entro **45 gg** dalla fine del trimestre | Niente short, niente bond, niente non-USA; è possibile ottenere il trattamento confidenziale |
| **Schedule 13D / 13G** | Chi supera il 5% di una società | Partecipazione e intenzioni (13D = attivista) | 13D: **10 gg** (regola SEC 2023; prima era più lungo) | Il segnale più tempestivo per gli attivisti |
| **Form 4** | Insider (dirigenti, consiglieri, azionisti sopra il 10%) | Ogni acquisto o vendita | **2 giorni lavorativi** | La fonte più veloce e più ricca di segnali |
| **PTR (STOCK Act)** | Membri del Congresso | Trade per fasce di importo | Fino a **45 gg** dalla transazione | Spesso in ritardo, importi solo per fasce |

[V] per il contenuto generale delle regole; le scadenze sono quelle normative note. La regola 13D a 10 giorni vale dal 2024 (emendamento SEC 2023): da ricontrollare prima di usarla in produzione.

### 1.3 Replicabili e non replicabili

- **Replicabili (bassa rotazione, posizioni long, concentrate):** Berkshire, Pershing Square, Li Lu (parte USA), Fundsmith (via factsheet), Akre, Markel, più in generale i "superinvestor" value elencati da Dataroma.
- **Replicabili solo in parte:** Druckenmiller, Tepper, Klarman. Il 13F è una piccola fetta di strategie macro o di credito; si copia un sottoinsieme che **non** è la strategia.
- **Non replicabili:** Renaissance/Medallion, Citadel, Two Sigma, Jane Street, Virtu e simili. Il 13F è una fotografia di posizioni che durano ore o giorni e arriva 45 giorni dopo.

---

## 2. Evidenza accademica sulla replica

### 2.1 Clonazione dei 13F e piggybacking

| Studio | Risultato | Affid. | URL |
|---|---|---|---|
| **Martin, G.S. & Puthenpurackal, J. (2008 circa), "Imitation is the Sincerest Form of Flattery: Warren Buffett and Berkshire Hathaway"** (SSRN 806246) | Portafoglio Berkshire 1976-2006: batte l'S&P di **~14,65%/anno**. Un portafoglio mimetico **costruito il mese dopo la disclosure** ottiene comunque **alfa positivo e significativo** (le stime riportate vanno dal 10,75% al 14,26%/anno secondo il metodo; un'altra sintesi parla di 7-10%) | [S]: numeri dai riassunti, PDF non letto integralmente | <https://www.cnbc.com/id/218.html>, <https://cxoadvisory.com/investing-expertise/buffetts-track-record-luck-or-skill>, <https://www.valuewalk.com/imitation-sincerest-form-flattery-warren-buffett-berkshire-hathaway/> |
| **Brown, S.J. & Schwarz, C., "Do Market Participants Care about Portfolio Disclosure? Evidence from Hedge Funds' 13F Filings"** (working paper, circa 2011-2013) | Documenta i **copycat** che inseguono i 13F degli hedge fund e la pressione sui prezzi alla data di deposito. Secondo il FT, gli autori **non trovano evidenza che le strategie copycat basate sui 13F diano benefici agli investitori di lungo periodo** | [S]: paper non letto, sintesi da FT/NYU e citazioni | <https://www.stern.nyu.edu/experience-stern/news/stephen-brown-ft-1-14>, CV di Schwarz: <https://business.columbia.edu/sites/default/files-efs/person/cv/cschwarz_CV_1123.pdf> |
| **Aragon, Hertzel & Shi (2013), JFQA, "Why Do Hedge Funds Avoid Disclosure? Evidence from Confidential 13F Filings"** | Le posizioni tenute riservate hanno più contenuto informativo: **il 13F pubblico è "ciò che il gestore accetta di mostrarti"** | [V] (abstract) | <https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/why-do-hedge-funds-avoid-disclosure-evidence-from-confidential-13f-filings/D26B3BC0EF07E387B4E80519565C33E8> |
| **Shi (2017), JFE** | La performance dei fondi cala di **circa il 4% annuo** dopo l'inizio dei depositi 13F (costo della disclosure) | [S] | citato in <https://webcentrum.muni.cz/media/3528254/13f_smart_money.pdf> |
| **Faber, M., *Invest with the House* (2016)** | Clone 13F di gestori selezionati: **9,8% CAGR contro 6,6% di SPY, 2000-2014**, lordo dei costi | [S] | <https://www.cxoadvisory.com/individual-investing/a-few-notes-on-invest-with-the-house/> |
| **Schroeder & Posch (2024), "Outperforming the Market: Portfolio Strategy Cloning from SEC 13F Filings"** | Clona 3.643 fondi 2013-2023. Una sintesi riporta che i cloni del **quartile migliore** replicano i fondi e battono l'S&P. Il dato "+24,25% risk-adjusted" **non è verificato** ed è sospettosamente alto | [I] | <https://www.cxoadvisory.com/miscellaneous/form-13f-clone-portfolio-performance/> |
| **Backtest WhaleWisdom (Appaloosa)** | Negli ultimi anni il clone **è circa pari all'S&P 500**; ricorda che il 13F omette short, bond e derivati | [S] | <https://whalewisdom.com/help/backtesting_whitepaper> |

**Lettura critica.** Il clone di Berkshire è il caso più solido, ma riguarda soprattutto 1976-2006, quando Berkshire era più piccola. Oggi Berkshire ha 300+ miliardi di dollari in liquidità e T-bill, che il 13F non mostra, e ha sottoperformato l'S&P nel 2025. Le slide Wharton (Ballesteros, Levine, Pasynkiewicz, 2022) concludono che copiare dai 13F "funziona nel lungo periodo", ma che è **molto difficile scegliere ex ante quali gestori continueranno a sovraperformare** (<https://finance.wharton.upenn.edu/~mrrobert/resources/Analytics/2022-blp-phase3-slides.pdf>) [S].

### 2.2 Insider (Form 4)

| Studio | Risultato | Affid. | URL |
|---|---|---|---|
| **Lakonishok, J. & Lee, I. (2001), "Are Insider Trades Informative?", RFS 14(1):79-111** | Gli **acquisti** degli insider predicono i rendimenti (soprattutto nelle **small cap**), le **vendite no**. Una sintesi di terzi riporta: acquisti forti contro vendite forti +7,8% a 12 mesi, ~4,8% dopo il controllo per size e B/M | [V] abstract, [S] numeri | <https://econpapers.repec.org/RePEc:oup:rfinst:v:14:y:2001:i:1:p:79-111> |
| **Cohen, L., Malloy, C. & Pomorski, L. (2012), "Decoding Inside Information", JF 67(3):1009-1043** | Separano i trade **routinari** (stesso mese ogni anno) da quelli **opportunistici**. Strategia long sugli opportunistici: **alfa value-weighted di 82 bp/mese**; i routinari hanno alfa **circa zero**. I routinari sono più della metà di tutti i trade. Gli insider più informati sono **non-esecutivi, locali, in aziende con governance debole** | [V] abstract | <https://econpapers.repec.org/RePEc:bla:jfinan:v:67:y:2012:i:3:p:1009-1043> |
| **Alldredge, D. & Blank, B. (2019), "Do Insiders Cluster Trades with Colleagues? Evidence from Daily Insider Trading", Journal of Financial Research 42(2):331-360** | Gli **acquisti in cluster** (più insider entro pochi giorni) sono seguiti da **rendimenti anomali superiori al 2% nel mese successivo** | [V] abstract | <https://ideas.repec.org/a/bla/jfnres/v42y2019i2p331-360.html> |

**Lettura critica.** È il segnale con l'evidenza accademica più robusta e il **ritardo più basso** (2 giorni). Due limiti: l'alfa si concentra nelle small e micro cap, dove spread e liquidità contano molto; inoltre i risultati sono pre-pubblicazione e potrebbero essersi ridotti (decadimento post-pubblicazione documentato in generale da McLean & Pontiff 2016, non verificato in questa sessione). **Il filtro routinario/opportunistico è implementabile con i dati gratuiti di EDGAR.**

### 2.3 Membri del Congresso

| Studio | Periodo | Risultato | Affid. | URL |
|---|---|---|---|---|
| **Ziobrowski et al. (2004, JFQA; 2011)** | Senato 1993-98; Camera 1985-2001 | Portafogli sintetici dai trade: Senato **+12%/anno**, Camera **+6%/anno** rispetto al mercato | [S] | via <https://www.mit.edu/~jhainm/Paper/CL.pdf> |
| **Eggers, A. & Hainmueller, J. (2013), "Capitol Losses: The Mediocre Performance of Congressional Stock Portfolios", Journal of Politics 75(2):535-551** | 2004-2008 | Usando le **posizioni reali**, i portafogli **sottoperformano** il mercato di ~2-3%/anno. Fanno eccezione le aziende del proprio distretto | [V] | <https://www.mit.edu/~jhainm/Paper/CL.pdf> |
| **Karadas (2019), The Financial Review** | pre/post 2012 | L'alfa positivo **scompare dopo lo STOCK Act** | [S] | via <https://www.thecgo.org/research/the-amendment-of-the-stock-act-and-the-prices-of-stocks-most-held-by-congress/> |
| **Belmont, Sacerdote, Sehgal & Van Hoek (2020), NBER WP 26975, "Relief Rally: Senators as Feckless as the Rest of Us at Stock Picking"** | 2012-2020 | **Nessuna evidenza** di sovraperformance dei senatori | [V] | <https://www.nber.org/papers/w26975> |
| **Wei, S.-J. & Zhou, Y. (2025), NBER WP 34524, "'Captain Gains' on Capitol Hill"** | 1995-2021, 20 leader | Prima di diventare leader rendono come i pari; **dopo, li battono di ~47 punti percentuali/anno**. Canali indicati: influenza politica e accesso alle aziende | [V] abstract | <https://www.nber.org/papers/w34524> |

**Lettura critica.** Il Congresso "in media" **non** batte il mercato dopo il 2012. L'eventuale segnale è concentrato in pochi leader e arriva **fino a 45 giorni dopo**, con importi solo per fasce. Gli ETF che seguono il Congresso (NANC, che replica i trade dei Democratici, e KRUZ, quelli dei Repubblicani, di Subversive/Unusual Whales) costano lo **0,75%/anno**. Nel 2025 i dati parziali danno NANC più o meno in linea con l'S&P [I]: nessun confronto pulito trovato. Nella migliore delle ipotesi è un segnale debole e di nicchia.

### 2.4 Copy trading e social trading

| Studio | Risultato | Affid. | URL |
|---|---|---|---|
| **Apesteguia, J., Oechssler, J. & Weidenholzer, S. (2020), "Copy Trading", Management Science 66(12):5608-5622** | Esperimento di laboratorio: vedere i risultati altrui **aumenta l'assunzione di rischio**, e la possibilità di **copiare** la aumenta **ancora di più**. Gli autori parlano di "excessive risk taking" | [V] | <https://econpapers.repec.org/RePEc:inm:ormnsc:v:66:y:12:i:2020:p:5608-5622> |
| **Pelster, M. & Hofmann, A. (2018)** | Le perdite sui trade copiati tendono a essere **maggiori** quando i rendimenti sono negativi (effetto disposizione / assunzione di rischio dei leader) | [S] | citato in <https://en.wikipedia.org/wiki/Copy_trading> |
| **Studio MIT / Altshuler (2012) su eToro** | Chi copiava i trader "suggeriti" faceva il 6-10% meglio di chi tradava manualmente. **Finanziato e promosso da eToro**, non peer-reviewed in finanza | [S] con conflitto di interessi | <https://www.financemagnates.com/forex/brokers/a-research-into-etoros-social-trading-shows-higher-returns/> |
| **Scientific Reports (2024), s41598-023-49648-3** | Su eToro i follower **aumentano il rischio** e **reagiscono in modo eccessivo** quando i signal provider aumentano il proprio | [S] | <https://www.nature.com/articles/s41598-023-49648-3.pdf> |
| **Tesi universitarie (Vienna, Tallinn)** | Nessuna sovraperformance consistente rispetto all'S&P 500 per campioni di portafogli copiati su eToro | [S], qualità bassa | <https://utheses-gateway.univie.ac.at/api/document/get/file/73534> |

**Lettura critica.** Non c'è evidenza indipendente che il copy trading retail generi alfa netto; c'è evidenza che **aumenta il rischio**. Le classifiche delle piattaforme soffrono di **survivorship bias**: i trader che falliscono spariscono dalla classifica.

### 2.5 Il retail in generale (base rate)

| Studio | Risultato | Affid. | URL |
|---|---|---|---|
| **Barber, B., Lee, Y.-T., Liu, Y.-J. & Odean, T. (2014), "The Cross-Section of Speculator Skill: Evidence from Day Trading", J. Financial Markets** | Taiwan 1992-2006: **meno dell'1%** dei day trader ottiene in modo prevedibile e ripetibile rendimenti anomali positivi al netto delle commissioni | [S] (testo dell'abstract riportato) | <https://moneyzine.com/investments/day-trading-statistics> |
| **Chague, F., De-Losso, R. & Giovannetti, B. (2020), "Day Trading for a Living?"** | Brasile, futures mini-Ibovespa: tra chi ha tradato più di 300 giorni, **circa il 97% ha perso denaro**, e solo l'1,1% ha guadagnato più del salario minimo | [S] | idem |

---

## 3. Soluzioni esistenti da usare o aggregare

> Principio: **i dati grezzi (13F, Form 4, PTR del Congresso) sono pubblici e gratuiti.** I servizi sotto vendono interfaccia, pulizia dei dati e alert. Con budget 0 € conviene fare ingestion diretta da EDGAR e usare i siti gratuiti solo come controllo incrociato manuale.

| Servizio | Cosa offre | Costo | API / scraping | Affid. |
|---|---|---|---|---|
| **SEC EDGAR** (fonte primaria) | Tutti i 13F, Form 4, 13D/G, in JSON su `data.sec.gov` e negli indici giornalieri | **Gratis**, nessuna chiave | API ufficiale. **Max 10 richieste/s**, `User-Agent` obbligatorio con nome ed email | [V] <https://www.sec.gov/os/accessing-edgar-data> |
| **House Clerk / Senate eFD** (fonte primaria Congresso) | PTR dei membri del Congresso | Gratis | Senato: ricerca web con disclaimer da accettare; Camera: zip annuali + PDF (spesso scansioni) | [I] (non riverificato in questa sessione) |
| **Dataroma** | 13F di circa 80 "superinvestor" value, attività trimestrale, insider "real-time", "Grand Portfolio" | Gratis | **Nessuna API.** `robots.txt` non servito (restituisce HTML). ToS non trovati, quindi scraping da considerare a rischio. Esistono scraper di terzi (Apify) | [I] |
| **WhaleWisdom** | 13F completi, backtest dei cloni, 13D/G, "WhaleScore" | Free: 2 anni di storico. Paid: circa 90 $/trimestre (Standard, con API) o 300 $/anno; Pro/Enterprise più cari | **API sui piani a pagamento**, ~20 richieste/min. Prezzi in conflitto tra le fonti | [I] <https://whalewisdom.com/pricing> |
| **HedgeFollow** | 13F, insider, alert | Free + premium (circa 99 $/anno secondo un concorrente) | Nessuna API trovata. Il `robots.txt` usa i "content signals" di Cloudflare (sono previste restrizioni sull'uso AI) | [I] <https://hedgefollow.com/plans.php> |
| **Quiver Quantitative** | Congresso, lobbying, contratti governativi, insider, WSB, 13F | Sito con piano free; API a partire da ~10-30 $/mese (Hobbyist, uso non commerciale); i prezzi variano tra le fonti | **API ufficiale + client Python `quiverquant` (PyPI) e un crate Rust `quiverquant`** | [I] prezzi; [V] esistenza API <https://api.quiverquant.com/datasets/congress-trades> |
| **Autopilot** (app) | Copia automatica di portafogli ("Pelosi Tracker", Buffett, ecc.) sul tuo broker collegato | ~99 $/anno (dato 2025) | Nessuna API; esegue sul broker USA collegato. Probabilmente **solo per residenti USA** [I]. AUM dichiarato di 1,3 mld $ (marzo 2026) | [S]/[I] <https://finviz.com/news/335508/exclusive-from-2-million-to-13-billion-autopilots-focus-on-pelosi-and-other-politicians-is-paying-off> |
| **Capitol Trades** (2iQ) | Trade del Congresso puliti, per politico e per ticker | **Gratis** (dichiarato dall'operatore) | **Nessuna API pubblica**; sito dietro il "Vercel Security Checkpoint" anti-bot (verificato), quindi scraping sconsigliato | [V] gratis <https://www.capitoltrades.com/about-us>; [V] anti-bot |
| **Unusual Whales** | Flusso opzioni, dark pool, Congresso (inclusi i "late reports"), ETF NANC/KRUZ | Sito in abbonamento. API (maggio 2025): Trial 50 $/settimana, Basic 150 $/mese, Advanced 375 $/mese | API ufficiale (`/api/congress/recent-trades` e altre). Fuori budget | [S] <https://unusualwhales.substack.com/p/unusual-whales-api-prices-increasing> |
| **openinsider.com** | Screener del Form 4: **"Cluster Buys"**, acquisti di CEO/CFO, filtri | Gratis | Nessuna API ufficiale. `robots.txt` blocca solo Semrush, dotbot e Ahrefs (verificato). Tabelle HTML facilmente parsabili, ma meglio fare ingestion diretta del Form 4 da EDGAR | [V] robots.txt |
| **eToro CopyTrader / Smart Portfolios** | Copia di trader retail; portafogli tematici | Copia **minimo 200 $** per trader (1 $ per posizione); Smart Portfolios **minimo 500 $** (pagine ufficiali eToro). Fee crypto 1%, prelievo ~5 $ [S] | **Nessuna API di trading pubblica per il copy**; il "copy" è dentro la piattaforma. **Con 50 € non si può copiare nessuno** | [V] minimi <https://www.etoro.com/trading/copytrader/how-it-works/> |
| **Composer** | Strategie "symphony" no-code (ETF/azioni), backtest, esecuzione automatica | Trading Pass ~24-40 $/mese (in conflitto) | API documentata (`api.composer.trade`). Account broker USA, storicamente via Alpaca. Residenti UE: [I] | [I] <https://help.composer.trade/article/120-pricing-billing> |
| **Collective2** | Marketplace di segnali con track record "verificato dalla piattaforma", autotrade | Abbonamento al singolo sistema fissato dal manager (tipicamente 50-200 $/mese) + fee della piattaforma | API per i manager e per gli abbonati. Fuori budget | [S] <https://support.collective2.com/hc/en-us/articles/202933794-What-are-the-fees-involved-with-AutoTrading> |
| **Disclosed Capitol** (alternativa) | Trade del Congresso con API REST, free tier per sviluppatori (dichiarato) | Free tier | API | [I] <https://www.disclosedcapitol.com/vs/capitol-trades> |

### 3.1 Broker esecutivi compatibili con 50 € (rilevante per l'aggregatore)

| Broker | API | Frazionamento | Note per un residente italiano | Affid. |
|---|---|---|---|---|
| **Alpaca** | REST/WebSocket ottimi, SDK Python/TS | Sì, da **1 $** | **Disponibilità del conto retail in Italia incerta**: un post utente di giugno 2026 dice "Trading API retail ora solo USA"; acquisizione di WealthKernel (UE) ad aprile 2026. **Il paper trading è disponibile a tutti** | [I] <https://alpaca.markets/global-stocks> |
| **Interactive Brokers** | TWS/Gateway API, Client Portal | Sì (azioni USA ed europee) | Disponibile in Italia; nessun minimo, ma **commissione minima per ordine** (indicativamente circa 1 $), pesantissima su 50 € | [I] sulle tariffe attuali |
| **Trading 212** | **API pubblica beta**: in live solo **ordini a mercato**, endpoint non idempotente, conto demo disponibile | Sì, zero commissioni | Disponibile in UE; è l'opzione più realistica per "50 € su azioni/ETF via API" | [V] <https://docs.trading212.com/api/orders> |
| **Exchange crypto** (Kraken, Binance, Bybit...) | Via ccxt / adapter Nautilus | Importi minimi di ordine bassi (pochi $) | Verificare la registrazione OAM/MiCA dell'exchange per l'Italia | [I] |

---

## 4. Framework open source di trading e backtest

Dati GitHub raccolti via API il **2026-11-06** [V].

| Progetto | Linguaggio | Stelle | Ultima release / attività | Licenza | Broker / venue | Idoneità a Rust+TS+Python |
|---|---|---|---|---|---|---|
| **NautilusTrader** (nautechsystems/nautilus_trader) | **Rust core + Python** (PyO3) | **31.3k** | Stabile **v1.231.0** (2026-08-02); **v2.0.0rc8** (2026-10-28, prerelease, più Rust-native: `LiveNode` con strategie Python incorporate). Commit oggi | **LGPL-3.0** | Adapter: **Interactive Brokers**, Binance, Bybit, Coinbase, Kraken, OKX, Hyperliquid, dYdX, Deribit, Databento, Tardis, Polymarket, Betfair... **Alpaca assente** tra gli adapter ufficiali | **Ottima**: stesso motore per backtest e live, core Rust estendibile, strategie in Python. LGPL va bene per uso personale |
| **QuantConnect LEAN** | C# (+ Python) | 22.4k | Commit oggi; release via tag/Docker (le "release" GitHub sono ferme al 2017) | Apache-2.0 | Repo dedicati: **Alpaca, IBKR, Binance, Kraken** e molti altri | Media: robusto, ma il core C#/.NET è fuori stack. Il cloud QC ha un piano gratuito con i dati inclusi |
| **freqtrade** | Python | **56.5k** | **2026.10** (2026-10-30) | GPL-3.0 | **Solo crypto** (via ccxt): Binance, Kraken, Bybit, OKX... | Buona per la crypto: maturo, hyperopt, dry-run, bot Telegram. Facile overfitting con hyperopt |
| **Hummingbot** | Python (+ Cython) | 21.0k | v2.17.0 (2026-09-22) | Apache-2.0 | Crypto CEX + DEX | Specializzato in **market making / arbitraggio**: non adatto all'idea "copia i grandi" |
| **backtrader** | Python | 23.7k | Ultimo commit **aprile 2023**; nessuna release | GPL-3.0 | IB, Oanda (legacy) | **Da evitare**: non mantenuto |
| **vectorbt** | Python (NumPy/Numba) | 9.7k | v1.2.0 (2026-10-19) | **Apache-2.0 + Commons Clause** (non si può vendere) | Solo backtest/ricerca | Ottimo per **ricerca vettoriale veloce** (sweep di parametri). La versione PRO è a pagamento |
| **zipline-reloaded** | Python | 2.0k | 3.2.1 (2026-10-25) | Apache-2.0 | Solo backtest (bundle dati) | Discreta per la ricerca fattoriale; ecosistema di nicchia |
| **Microsoft Qlib** | Python | **50.1k** | v0.9.8 (2026-10-08) | MIT | Ricerca ML (dati di default focalizzati sulla Cina) | Utile per la **ricerca ML/alpha**, non per l'esecuzione |
| **FinRL** | Python | 17.0k | v0.3.8 (2026-03-20) | MIT | Alpaca (esempi) | Accademico (RL). Altissimo rischio di overfitting; non usare come base |
| **Jesse** | Python | 8.8k | tag v3.6.0; commit oggi | MIT | Crypto | Alternativa a freqtrade, più pulita ma più piccola |
| **barter-rs** | **Rust** | 2.4k | barter-macro v0.2.1 (2026-08-20) | MIT | Crypto: Binance, Bitfinex, BitMEX, Bybit, Coinbase, Gate.io, Kraken, OKX | Buona libreria Rust nativa, ma **niente azioni / IBKR / Alpaca**; da usare come componenti |
| **hftbacktest** | Rust (+ Python) | 5.1k | Ultimo push 2025-12 | MIT | Binance/Bybit (HFT, order book L2/L3) | Fuori scopo (HFT) |
| **backtesting.py** | Python | 9.2k | Push 2026-08 | **AGPL-3.0** | Solo backtest | Semplice, ma AGPL |
| **ccxt** (libreria) | TS/JS, Python, PHP, C#, Go | **44.8k** | Commit 2026-11-05 | MIT | 100+ exchange crypto | **Fondamentale** per la crypto lato TS/Python |
| **edgartools** (libreria) | Python | 2.8k | Commit oggi | MIT | Parsing di **13F, Form 4**, 10-K da EDGAR | **Fondamentale** per l'ingestion dei segnali |
| **alpaca-py** (SDK) | Python | 1.6k | Commit oggi | Apache-2.0 | Alpaca | Se Alpaca è accessibile |

Fonti: `gh api repos/<owner>/<repo>` e `/releases`, eseguiti il 2026-11-06. Elenco degli adapter Nautilus da `nautilus_trader/adapters/` su GitHub; exchange di barter da `barter-data/src/exchange/`.

---

## 5. Casi reali retail e fallimenti comuni

### 5.1 Casi di successo documentati

- **Non ho trovato nessun bot retail con track record live verificato da terzi** (audit o dati collegati direttamente all'exchange) per freqtrade o simili. I risultati della ricerca erano autodichiarati, quasi sempre **dry-run** o backtest (es. post su dev.to con "679% win rate" in backtest, 48 trade in pareggio in dry-run, un bot che in 44 giorni non ha fatto nessun trade) [V che si tratta di autodichiarazioni]. Fonti: <https://dev.to/trendrider/13-days-48-trades-breakeven-then-i-fixed-one-thing-1d6j>
- Le piattaforme con track record "verificato" (Collective2, Myfxbook "Track record verified") verificano che i **dati siano veri**, non che la strategia abbia **edge**, e sono soggette a survivorship bias.
- **Quantopian** (crowdsourcing di algoritmi retail per un hedge fund) ha chiuso nel 2020 dopo risultati deludenti del fondo [S, noto]. È il caso più vicino a un esperimento su larga scala di "retail che costruisce algoritmi", ed è finito male.

### 5.2 Fallimenti più comuni (con evidenza)

| Errore | Evidenza | Contromisura |
|---|---|---|
| **Overfitting / data snooping** | Wiecki, Campbell, Lent & Stauth (2016), "All that Glitters Is Not Gold" (Quantopian, 888 algoritmi): lo **Sharpe in backtest spiega meno del 2,5% (R² < 0,025)** dello Sharpe out-of-sample. Più backtest si fanno, peggiore è il divario [S] <https://quantpedia.com/quantopians-academic-paper-about-in-vs-out-of-sample-performance-of-trading-alg/> | Walk-forward, holdout intoccato, **Probability of Backtest Overfitting** (Bailey, Borwein, López de Prado & Zhu, J. Computational Finance 2017) [V] <https://papers.ssrn.com/abstract=2326253>, **Deflated Sharpe Ratio** (Bailey & López de Prado), registro di tutti i tentativi |
| **Costi e slippage ignorati** | Con 50 € una commissione fissa di 1 € vale il 2% per trade. Gli studi sui day trader (Taiwan, Brasile) mostrano perdite quasi universali al netto dei costi | Broker a zero commissioni con frazionamento, bassa rotazione (ribilanciamento mensile o trimestrale), modello dei costi nel backtest |
| **Look-ahead bias** | Errore classico: usare il 13F alla **data di fine trimestre** invece che alla **data di deposito** (fino a 45 giorni dopo); usare i prezzi di chiusura per decidere alla stessa chiusura | Indicizzare ogni segnale con `filed_at` / `accepted_at` di EDGAR; eseguire alla barra successiva |
| **Survivorship bias** | Universi azionari "di oggi" applicati al passato; classifiche di copy trading solo con i sopravvissuti | Dataset point-in-time con i delisted; per i gestori, scegliere la lista ex ante e non a posteriori |
| **Decadimento del segnale** | Segnali pubblicati in letteratura tendono a perdere efficacia dopo la pubblicazione; per il Congresso l'alfa sparisce dopo il 2012 | Paper trading di 3-6 mesi prima di andare live; monitoraggio continuo |
| **Aumento del rischio da copia** | Apesteguia et al. (2020) | Position sizing fisso, niente leva, stop di portafoglio |

---

## 6. Cosa è verificato e cosa è incerto

**Verificato [V]**
- Berkshire 1965-2025: 19,7% contro 10,5%/anno (lettera 2025, Greg Abel CEO).
- Pershing Square: rendimenti dall'Annual Report 2025 PSH.
- Burry/Scion: registrazione SEC terminata il 10/11/2025.
- Abstract di Cohen-Malloy-Pomorski (82 bp/mese), Lakonishok-Lee, Alldredge-Blank, Eggers-Hainmueller, Belmont et al., Wei-Zhou ("Captain Gains"), Apesteguia et al.
- Limiti SEC EDGAR (10 richieste/s, User-Agent).
- Minimi eToro (200 $ per il copy, 500 $ per gli Smart Portfolios).
- API Trading 212 beta con soli ordini a mercato in live.
- Statistiche GitHub e licenze di tutti i framework; adapter NautilusTrader (IBKR sì, Alpaca no); broker LEAN (Alpaca, IBKR, Binance, Kraken).
- `robots.txt` di openinsider; Capitol Trades dietro protezione anti-bot.

**Incerto [I]**
- Rendimenti esatti di Medallion (dal libro di Zuckerman, non auditati), Li Lu, Klarman, Tepper, Druckenmiller (anno 2010).
- I numeri precisi di Martin & Puthenpurackal (le sintesi divergono tra 7% e 14%).
- Il risultato "+24,25%" di Schroeder & Posch (2024).
- Prezzi attuali di WhaleWisdom, Quiver, HedgeFollow, Composer, Collective2 e Autopilot.
- ToS di Dataroma.
- Disponibilità di Alpaca retail e Autopilot per residenti italiani.
- Commissioni minime attuali di IBKR.
- Performance di NANC/KRUZ contro l'S&P nel 2025.

---

## 7. Raccomandazioni

### 7.1 Cosa replicare (in ordine di evidenza e fattibilità)

1. **Acquisti insider "opportunistici" e in cluster (Form 4).** È il segnale con l'evidenza accademica più forte (CMP 2012, Alldredge-Blank 2019) e il ritardo più basso (2 giorni). Dati gratis da EDGAR. Filtro: escludere i trade routinari (stesso mese negli ultimi 3 anni), considerare solo gli **acquisti** (le vendite non hanno valore predittivo), dare priorità a cluster di 2 o più insider e ai dirigenti C-level, ed escludere le micro cap illiquide che con un capitale piccolo non sono eseguibili in modo sensato.
2. **Paniere "superinvestor value" dai 13F** (Berkshire, Pershing Square, Li Lu, Akre, Markel e simili): consenso delle posizioni ad alta convinzione (peso maggiore del 5% nel portafoglio del gestore) presenti in 2 o più gestori. Ribilanciamento **trimestrale alla data di deposito**. Aspettativa realistica: **circa pari al mercato, con possibile piccolo alfa**. Va trattato come "core", non come motore di alfa.
3. **Congresso: solo come feature secondaria**, eventualmente limitata ai **leader** (Wei-Zhou 2025). Nessuna strategia dedicata: l'evidenza post-STOCK Act è negativa in media.
4. **Da non replicare:** Renaissance e i quant/HFT, il copy trading eToro (minimo 200 $ e più rischio senza alfa provato), i macro trader via 13F (Druckenmiller, Tepper), e Burry (non più osservabile).

### 7.2 Cosa aggregare (budget 0 €)

- **Ingestion primaria:** SEC EDGAR (`data.sec.gov` + indici giornalieri) con **edgartools** in Python per 13F e Form 4. Per i PTR del Congresso: Senate eFD / House Clerk, oppure il free tier di Quiver/Disclosed Capitol se esistente [I].
- **Controllo incrociato manuale (niente scraping):** Dataroma, openinsider (cluster buys), Capitol Trades, WhaleWisdom free.
- **Crypto:** non esiste un equivalente del 13F affidabile. Si può usare **ccxt** per i dati di mercato e tenere la crypto come allocazione separata e semplice (es. DCA o trend-following basilare), non come "copia dei grandi".

### 7.3 Framework base

- **Base: NautilusTrader.** Core Rust (coerente con lo stack), strategie in Python, stessa codepath per backtest e live, adapter **IBKR** e i principali exchange crypto, sviluppo molto attivo (2.0 in RC). Licenza LGPL accettabile per uso personale. Mancano Alpaca e Trading 212: se servono, scrivere un adapter custom (l'API Trading 212 è semplice) oppure usare un piccolo servizio TS/Python separato per gli ordini.
- **Ricerca veloce:** **vectorbt** (sweep e analisi) e i notebook Python; usare PBO e Deflated Sharpe prima di andare live.
- **Crypto standalone (opzionale):** freqtrade se si vuole un bot crypto pronto, con dry-run, senza scrivere il motore.
- **Da scartare come base:** backtrader (abbandonato), FinRL/Qlib (ricerca, non esecuzione), Hummingbot (market making), LEAN (C#, fuori stack, anche se ottimo).
- **Ruolo di TypeScript:** dashboard e orchestrazione (ccxt ha binding TS nativi); Rust per il core e per gli adapter custom; Python per strategie, ricerca e ingestion SEC.

### 7.4 Vincolo pratico con 50 €

Con 50 € l'obiettivo realistico è **validare la pipeline** (ingestion → segnale → ordine → logging) in **paper trading** (Alpaca paper, conto demo Trading 212, IBKR paper, dry-run di freqtrade), non generare reddito. Una sovraperformanza del 5%/anno vale **2,50 €/anno**. Prima di mettere soldi veri servono 3-6 mesi di paper trading con modello dei costi realistico. Live solo su broker a zero commissioni con frazionamento, con 5-10 posizioni al massimo e ribilanciamento mensile o trimestrale.
