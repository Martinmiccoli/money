# Bibliografia di riferimento: trading algoritmico retail

> Data di compilazione: 2026-11-06
> Contesto: progetto personale, capitale 50 €, micro-transazioni, stack Rust + TypeScript + Python.
> Pilastri: matematica e statistica, predizioni, ML, sentiment/narrazione, replica degli investitori top, gestione del rischio.

## Legenda verifica

| Stato | Significato |
|---|---|
| **VERIFICATA** | Titolo, autori, anno (e DOI/ID dove presente) confermati con una ricerca web il 2026-11-06; l'URL indicato è quello consultato o il DOI risolvibile. |
| **PARZIALE** | Esistenza confermata, ma un dettaglio (anno di un'edizione, numero di pagine, cifra esatta) non è stato confermato da più fonti. Il dettaglio incerto è segnalato. |
| **NON VERIFICATA** | Riportata per completezza ma senza conferma web in questa sessione. Da controllare prima di citarla. |

I risultati numerici dei paper sono riassunti dall'abstract o da fonti secondarie affidabili (EconPapers, arXiv, pagine degli autori). Non ho riletto tutti i full text: dove una cifra viene da una sola fonte secondaria, lo indico.

---

## 1. Libri fondamentali

### 1.1 Investimento classico

| Libro | Stato | Cosa prendere per il nostro sistema |
|---|---|---|
| **Benjamin Graham, *The Intelligent Investor*** (1949; ed. rivista 2003 con commento di Jason Zweig, HarperBusiness) | VERIFICATA ([OpenLibrary 1949](https://openlibrary.org/books/OL273184W), [OpenLibrary 2003](https://openlibrary.org/works/OL21152532W)) | Il "Mr. Market" va trattato come una controparte emotiva da sfruttare, non da seguire. **Margine di sicurezza** = principio di sizing conservativo. La distinzione investitore difensivo/intraprendente ci serve come baseline: con 50 € la strategia difensiva (indicizzata) è il benchmark che ogni modello deve battere al netto dei costi. |
| **Philip A. Fisher, *Common Stocks and Uncommon Profits*** (1958; ristampa Wiley 1996 "...and Other Writings") | VERIFICATA ([Goldmoney library](https://goldmoney.com/research/library/common-stocks-and-uncommon-profits-philip-fisher-1958), [Wiley 1996](https://www.schweitzer-online.de/en/buch/Fisher/Common-Stocks-Uncommon-Profits/9780471119289/A2089782/)) | Il metodo "scuttlebutt" (raccogliere voci da clienti, fornitori e concorrenti) è l'antenato qualitativo del nostro pilastro sentiment. I 15 punti di Fisher si possono usare come checklist di feature qualitative estraibili con un LLM dai documenti societari. |
| **Peter Lynch (con J. Rothchild), *One Up on Wall Street*** (Simon & Schuster, 1989) | VERIFICATA ([CS Monitor, recensione 1989](https://www.csmonitor.com/1989/0428/dbwall.html)) | Classificare le aziende (slow grower, stalwart, fast grower, cyclical, turnaround, asset play) è un utile schema di regimi e etichette. L'idea "investi in ciò che conosci" è un segnale di attenzione: ha pro e contro, vedi Da-Engelberg-Gao e Barber et al. su Robinhood. |
| **Burton G. Malkiel, *A Random Walk Down Wall Street*** (1ª ed. 1973; 13ª ed. "50th anniversary", W. W. Norton, 2023/2024) | PARZIALE: la 1ª ed. 1973 è confermata ([OpenLibrary](https://openlibrary.org/books/OL387646M)); l'anno della 13ª ed. varia tra le fonti (2023 o 2024) | È l'ipotesi nulla del progetto: i prezzi sono quasi imprevedibili e ogni segnale va testato contro un random walk. I capitoli su smart beta e costi spiegano perché la gestione passiva vince la maggior parte delle volte. |
| **John C. Bogle, *The Little Book of Common Sense Investing*** (Wiley, 2007; ed. 10° anniversario 2017) | PARZIALE: la pubblicazione Wiley è confermata, gli anni 2007/2017 no ([Fool.com list](https://www.fool.com/investing/how-to-invest/best-investing-books-for-beginners)) | È l'aritmetica dei costi: il rendimento netto è il lordo meno i costi, e per un trader attivo i costi crescono con la frequenza. Con 50 € una commissione fissa di 1 € vale il 2% per ogni operazione: va internalizzato come vincolo duro. |

### 1.2 Quant e trading algoritmico

| Libro | Stato | Cosa prendere |
|---|---|---|
| **Marcos López de Prado, *Advances in Financial Machine Learning*** (Wiley, 2018, ISBN 978-1-119-48208-6) | VERIFICATA ([Wiley-VCH](https://www.wiley-vch.de/en/areas-interest/finance-economics-law/advances-in-financial-machine-learning-978-1-119-48208-6)) | Il testo base per la pipeline ML. Da prendere: barre di volume, dollar e information bar al posto delle time bar; triple-barrier labeling e meta-labeling; purged/embargoed k-fold CV; frazionale differencing; feature importance MDI/MDA/SFI; combinatorial purged CV; deflated Sharpe ratio. Va implementato in Python (ricerca), con il motore di backtest in Rust. |
| **Ernest P. Chan, *Quantitative Trading*** (Wiley, 1ª ed. 2008; 2ª ed. luglio 2021, ISBN 978-1-119-80006-4) | VERIFICATA per la 2ª ed. ([O'Reilly](https://www.oreilly.com/library/view/quantitative-trading-2nd/9781119800064/c01.xhtml)) | Pensato per il trader indipendente con capitale piccolo. Da prendere: come costruire un'infrastruttura minima, come stimare la capacità di una strategia, il Kelly applicato in pratica, i bias di backtest (look-ahead, survivorship). |
| **Ernest P. Chan, *Algorithmic Trading: Winning Strategies and Their Rationale*** (Wiley, 2013) | VERIFICATA ([TUM catalog](https://search.ub.tum.de/vufind/Record/DE-604.BV041911311)) | Mean reversion (test ADF, Hurst, half-life, cointegrazione, pair trading) e momentum (time-series e cross-section). Ogni strategia è accompagnata dalla sua *rationale* economica. È il catalogo più concreto di strategie candidate. |
| **Rishi K. Narang, *Inside the Black Box*** (Wiley; 1ª ed. 2009, 2ª 2013, 3ª ed. "A Simple Guide to Systematic Investing") | PARZIALE: la 3ª ed. esiste ([IBS](https://www.ibs.it/inside-black-box-ebook-inglese-rishi-k-narang/e/9781119931904)), l'anno (circa 2024) non è confermato | L'architettura canonica di un sistema quant: alpha model, risk model, transaction cost model, portfolio construction, execution. Va usata come schema dei moduli del nostro codice. |
| **Gregory Zuckerman, *The Man Who Solved the Market*** (Portfolio/Penguin, 5 nov. 2019) | VERIFICATA ([Publishers Weekly](https://www2.publishersweekly.com/9780735217980)) | Una lezione di umiltà: Renaissance vince con moltissimi segnali deboli, dati puliti, esecuzione industriale e leva, non con una "formula". Il Medallion ha capacità limitata. Per noi: non c'è un segnale magico, conta l'infrastruttura di ricerca. |
| **Richard C. Grinold, Ronald N. Kahn, *Active Portfolio Management*** (McGraw-Hill; 1ª ed. 1995; 2ª ed. ©2000, uscita ott. 1999, ISBN 0070248826) | VERIFICATA per la 2ª ed. ([catalogo UiTM](https://search.library.uitm.edu.my/Record/wils-213647/Description)) | **Legge fondamentale**: IR ≈ IC × √Breadth. Un IC piccolo (0,02-0,05) è realistico; serve breadth, cioè molte scommesse indipendenti, ma con 50 € la breadth è limitata dai costi fissi. Da prendere anche: alpha = vol × IC × z-score, la neutralizzazione e il refining dei segnali. |
| **Stefan Jansen, *Machine Learning for Algorithmic Trading*** (Packt, 2ª ed. luglio 2020) | VERIFICATA ([O'Reilly](https://www.oreilly.com/library/view/-/9781839217715/)) | Un ricettario Python end-to-end: dati alternativi, NLP su filing e transcript, gradient boosting, LSTM, RL, Alphalens/pyfolio. Il codice del libro è il punto di partenza dei notebook di ricerca. Alcune librerie (Zipline) sono ormai poco mantenute. |

### 1.3 Rischio e sizing

| Libro / testo | Stato | Cosa prendere |
|---|---|---|
| **Edward O. Thorp, *A Man for All Markets*** (Random House, gen. 2017) | VERIFICATA ([Kirkus](https://kirkusreviews.com/book-reviews/edward-o-thorp/a-man-for-all-markets)) | Il Kelly è applicato da chi l'ha usato davvero (blackjack, warrant, Princeton-Newport). Dà la disciplina del vantaggio misurabile prima di scommettere. |
| **E. O. Thorp, "The Kelly Criterion in Blackjack, Sports Betting and the Stock Market"**, cap. 9 di *Handbook of Asset and Liability Management* vol. 1 (Elsevier, 2006) | VERIFICATA ([PDF gwern](https://www.Gwern.net/doc/statistics/decision/2006-thorp.pdf), [Elsevier](https://shop.elsevier.com/books/handbook-of-asset-and-liability-management/zenios/978-0-444-50875-1)) | È il riferimento tecnico per Kelly continuo: f* = μ/σ² per un asset. Mostra perché il half-Kelly sacrifica circa il 25% della crescita ma dimezza la volatilità. |
| **William Poundstone, *Fortune's Formula*** (Hill and Wang, 2005) | VERIFICATA ([Kirkus](https://www.kirkusreviews.com/book-reviews/william-poundstone/fortunes-formula/print), [Macmillan](https://academic.macmillan.com/academictrade/9780809045990/fortunesformula)) | La storia del Kelly (Shannon, Thorp) e il dibattito con Samuelson. È utile per capire i limiti del criterio. |
| **Ralph Vince, *The Mathematics of Money Management*** (Wiley, 1992) | VERIFICATA ([eBay listing 1992 Wiley](https://www.ebay.co.uk/p/1001966), [KTH thesis](https://www.math.kth.se/matstat/seminarier/reports/M-exjobb12/121105.pdf)) | L'"optimal f" è il Kelly empirico calcolato sulla lista dei trade. È molto aggressivo e sensibile alla perdita massima stimata, quindi va usato solo come limite superiore teorico. |
| **Nassim N. Taleb, *Fooled by Randomness*** (2001) e ***The Black Swan*** (Random House, 2007) | PARZIALE: *Fooled* 2001 è confermato ([Wikipedia](https://en.wikipedia.org/wiki/Fooled_by_Randomness)); *Black Swan* 2007 non è confermato in questa sessione | Survivorship bias, code grasse, non scambiare fortuna per abilità. Per noi: niente strategie con payoff "picking pennies in front of a steamroller" (short volatility, martingale), e stress test sulle code. |

### 1.4 Finanza comportamentale e narrazione ("fede del mercato")

| Libro | Stato | Cosa prendere |
|---|---|---|
| **Daniel Kahneman, *Thinking, Fast and Slow*** (Farrar, Straus and Giroux, 2011) | VERIFICATA ([MIT Press Bookstore](https://mitpressbookstore.mit.edu/book/9780374275631)) | Sistema 1 e Sistema 2, ancoraggio, avversione alle perdite, overconfidence. Sono i bias della controparte retail (da sfruttare) e i nostri (da automatizzare via regole). |
| **Robert J. Shiller, *Irrational Exuberance*** (Princeton UP, 2000; 3ª ed. rivista 2015) | VERIFICATA ([IDEAS/RePEc](https://ideas.repec.org/b/pup/pbooks/10421.html), [OpenLibrary](https://openlibrary.org/books/OL7759053M/Irrational_Exuberance)) | Feedback loop prezzo → storia → prezzo, CAPE come misura di valutazione di lungo periodo. È un regime filter macro, non un segnale di timing a breve. |
| **Robert J. Shiller, *Narrative Economics*** (Princeton UP, ott. 2019) | VERIFICATA ([De Gruyter DOI 10.1515/9780691212074](https://www.degruyterbrill.com/document/doi/10.1515/9780691212074/html)) | È la base teorica del pilastro "fede/narrazione": le narrazioni si diffondono come epidemie (modelli SIR). Idea operativa: misurare la *viralità* di un tema (frequenza, accelerazione, contagio tra fonti) con NLP, non solo la polarità del sentiment. |

---

## 2. Paper chiave

### 2.1 Fattori e anomalie

| Paper | Risultato principale | Link | Stato |
|---|---|---|---|
| Fama, French (1993), "Common risk factors in the returns on stocks and bonds", *JFE* 33:3-56 | Il modello a 3 fattori (mercato, size SMB, value HML) spiega gran parte della cross-section dei rendimenti azionari. | [doi:10.1016/0304-405X(93)90023-5](https://doi.org/10.1016/0304-405X(93)90023-5) | VERIFICATA |
| Fama, French (2015), "A five-factor asset pricing model", *JFE* 116(1):1-22 | Aggiunge profitability (RMW) e investment (CMA). Con questi due fattori HML diventa ridondante. | [doi:10.1016/j.jfineco.2014.10.010](https://doi.org/10.1016/j.jfineco.2014.10.010) | VERIFICATA |
| Jegadeesh, Titman (1993), "Returns to Buying Winners and Selling Losers", *JF* 48(1):65-91 | Il momentum cross-sectional a 3-12 mesi rende circa 1% al mese; parte del guadagno si inverte nel lungo periodo. | [doi:10.1111/j.1540-6261.1993.tb04702.x](https://doi.org/10.1111/j.1540-6261.1993.tb04702.x) | VERIFICATA |
| Carhart (1997), "On Persistence in Mutual Fund Performance", *JF* 52(1):57-82 | Il modello a 4 fattori (+ momentum) spiega quasi tutta la persistenza dei fondi; non c'è evidenza di abilità persistente salvo nei fondi peggiori. | [doi:10.1111/j.1540-6261.1997.tb03808.x](https://doi.org/10.1111/j.1540-6261.1997.tb03808.x) | VERIFICATA |
| Asness, Moskowitz, Pedersen (2013), "Value and Momentum Everywhere", *JF* 68(3):929-985 | Premi di value e momentum in 8 mercati e asset class, con una forte struttura fattoriale comune. Value e momentum sono correlati negativamente, quindi combinarli diversifica. | [doi:10.1111/jofi.12021](https://doi.org/10.1111/jofi.12021) · [PDF](https://pages.stern.nyu.edu/~lpederse/papers/ValMomEverywhere.pdf) | VERIFICATA |
| Moskowitz, Ooi, Pedersen (2012), "Time series momentum", *JFE* 104(2):228-250 | Il rendimento a 12 mesi di un asset predice il suo rendimento futuro in 58 futures liquidi (azioni, valute, commodity, bond). Le repliche mostrano che gran parte del risultato dipende dal *volatility scaling*. | [doi:10.1016/j.jfineco.2011.11.003](https://doi.org/10.1016/j.jfineco.2011.11.003) · [SSRN 2089463](https://papers.ssrn.com/abstract=2089463) | VERIFICATA |
| Harvey, Liu, Zhu (2016), "...and the Cross-Section of Expected Returns", *RFS* 29(1):5-68 | Con centinaia di fattori testati, la soglia t=2 non basta: un nuovo fattore dovrebbe avere **t > 3,0**. Molti fattori pubblicati sono probabilmente falsi positivi. | [doi:10.1093/rfs/hhv059](https://doi.org/10.1093/rfs/hhv059) · [NBER w20592](https://econpapers.repec.org/RePEc:nbr:nberwo:20592) | VERIFICATA |
| McLean, Pontiff (2016), "Does Academic Research Destroy Stock Return Predictability?", *JF* 71(1):5-32 | Su 97 anomalie, il rendimento cala di circa il 26% fuori campione e di circa il **58% dopo la pubblicazione**. Il calo è maggiore per le anomalie più facili da arbitraggiare. | [doi:10.1111/jofi.12365](https://doi.org/10.1111/jofi.12365) | VERIFICATA (titolo e DOI); le cifre 26%/58% vengono dall'abstract pubblicato e sono da ricontrollare sul full text |
| Hou, Xue, Zhang (2020), "Replicating Anomalies", *RFS* | Su 447 anomalie, il 64% non è significativo con breakpoint NYSE e pesi value-weighted; quasi tutte le anomalie di liquidità falliscono. | [NBER w23394](https://www.nber.org/papers/w23394.pdf) | PARZIALE (verificato il WP NBER; dati di pubblicazione RFS non controllati) |
| Jensen, Kelly, Pedersen (2023), "Is There a Replication Crisis in Finance?", *JF* | È la controreplica a HXZ: con un modello bayesiano e 153 fattori in 93 paesi, la maggioranza dei fattori replica (con alpha CAPM). | [PDF CBS](https://research-api.cbs.dk/ws/portalfiles/portal/95651880/theis_ingerslev_jensen_et_al_is_there_a_replication_crisis_in_finance_publishersversion.pdf) | VERIFICATA (esistenza); il tasso esatto di replica varia tra le fonti |
| Novy-Marx, Velikov (2016), "A Taxonomy of Anomalies and Their Trading Costs", *RFS* 29(1):104-147 | Le anomalie a basso turnover (value, profitability) sopravvivono ai costi di transazione. Quelle ad alto turnover (reversal a breve, alcune di momentum) perdono gran parte o tutto il rendimento. | [doi:10.1093/rfs/hhv063](https://doi.org/10.1093/rfs/hhv063) · [PDF](https://mysimon.rochester.edu/novy-marx/research/ToAatTC.pdf) | VERIFICATA |
| DeMiguel, Garlappi, Uppal (2009), "Optimal Versus Naive Diversification: How Inefficient is the 1/N Portfolio Strategy?", *RFS* 22(5):1915-1953 | Nessuno dei 14 modelli di ottimizzazione batte in modo consistente l'equal-weight 1/N fuori campione, perché l'errore di stima mangia i guadagni teorici. | [doi:10.1093/rfs/hhm075](https://doi.org/10.1093/rfs/hhm075) | VERIFICATA |

### 2.2 Machine learning e validazione

| Paper | Risultato principale | Link | Stato |
|---|---|---|---|
| Gu, Kelly, Xiu (2020), "Empirical Asset Pricing via Machine Learning", *RFS* 33(5):2223-2273 | Alberi e reti neurali battono i modelli lineari nel predire rendimenti mensili cross-section (R² OOS mensile intorno allo 0,4%, piccolo ma economicamente rilevante). Il guadagno viene dalle interazioni non lineari. I segnali dominanti sono momentum, liquidità e volatilità. | [doi:10.1093/rfs/hhaa009](https://doi.org/10.1093/rfs/hhaa009) · [NBER w25398](https://nber.org/papers/w25398) | VERIFICATA (il valore di R² viene dalla mia conoscenza del paper, da ricontrollare) |
| Bailey, Borwein, López de Prado, Zhu (2017), "The Probability of Backtest Overfitting", *J. Computational Finance* 20(4) | Introduce la **PBO** e il metodo **CSCV** (combinatorially symmetric cross-validation). Hold-out singolo e CV standard sono inaffidabili per i backtest finanziari. | [doi:10.21314/JCF.2016.322](https://doi.org/10.21314/JCF.2016.322) · [SSRN 2326253](https://papers.ssrn.com/abstract=2326253) | VERIFICATA |
| Bailey, López de Prado (2014), "The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality", *JPM* 40(5):94-107 | Il DSR corregge lo Sharpe per il numero di prove effettuate e per skewness e curtosi. È uno strumento obbligatorio quando si testano molte varianti. | [doi:10.3905/jpm.2014.40.5.094](https://doi.org/10.3905/jpm.2014.40.5.094) · [SSRN 2460551](https://papers.ssrn.com/abstract=2460551) | VERIFICATA |
| López de Prado (2018), "The 10 Reasons Most Machine Learning Funds Fail", *JPM* 44(6) | Elenca 10 errori: lavoro in silos, time bar, etichette a orizzonte fisso, CV con leakage, backtest overfitting e altri. | [GARP PDF](https://www.garp.org/white-paper/the-10-reasons-most-machine-learning-funds-fail) | VERIFICATA (esistenza); l'elenco esatto dei 10 punti non è stato riletto |
| Das, Kong, Sen, Zhou (2023/2024), "A decoder-only foundation model for time-series forecasting" (**TimesFM**), ICML 2024 | Un transformer decoder-only pre-addestrato su circa 100 miliardi di punti (Google Trends, Wikipedia). Lo zero-shot è vicino ai modelli supervisionati sui benchmark generici, **non** finanziari. | [arXiv:2310.10688](https://arxiv.org/abs/2310.10688) | VERIFICATA |
| Ansari et al. (2024), "Chronos: Learning the Language of Time Series" | Tokenizza le serie (scaling + quantizzazione) e addestra LM standard (T5) con cross-entropy. | [arXiv:2403.07815](https://arxiv.org/abs/2403.07815) | VERIFICATA |
| "Re(Visiting) Time Series Foundation Models in Finance" (2025) | Sui rendimenti giornalieri in eccesso, i TSFM zero-shot vanno **male**: R² OOS negativo (Chronos-large circa −1,4%, TimesFM circa −2,8%), accuratezza direzionale di circa il 51%. Sono **battuti da CatBoost/LightGBM**. Il fine-tuning sui dati finanziari aiuta, ma l'R² resta negativo. | [arXiv:2511.18578](https://arxiv.org/abs/2511.18578) | VERIFICATA (cifre dall'abstract/HTML v1) |
| "Pretrained Time-Series Foundation Models for Financial Return Forecasting" (giugno 2026) | Su 5 titoli USA, TimesFM-2.5 e Moirai-2.0 hanno il miglior rank medio sull'errore di previsione. Il test di Diebold-Mariano è significativo solo in 2 casi su 10, e il paper **non valuta la profittabilità**. | [arXiv:2606.27100](https://arxiv.org/abs/2606.27100) | VERIFICATA (abstract) |

**Sintesi sui foundation model per serie temporali:** a fine 2026 non c'è evidenza che i TSFM zero-shot predicano rendimenti azionari in modo sfruttabile. Possono servire come feature (ad esempio per previsioni di volatilità o volume, dove c'è più struttura), non come oracolo del prezzo.

### 2.3 Sentiment, attenzione e narrazione

| Paper | Risultato principale | Link | Stato |
|---|---|---|---|
| Tetlock (2007), "Giving Content to Investor Sentiment: The Role of Media in the Stock Market", *JF* 62(3):1139-1168 | Un alto pessimismo nella colonna WSJ "Abreast of the Market" predice pressione al ribasso sul Dow, seguita da un **ritorno ai fondamentali** in pochi giorni. Il sentiment media è rumore temporaneo, non informazione. | [doi:10.1111/j.1540-6261.2007.01232.x](https://doi.org/10.1111/j.1540-6261.2007.01232.x) · [SSRN 685145](https://papers.ssrn.com/abstract=685145) | VERIFICATA |
| Bollen, Mao, Zeng (2011), "Twitter mood predicts the stock market", *J. Computational Science* | Dichiarava un'accuratezza dell'87,6% nel predire la direzione giornaliera del DJIA con il "mood" Twitter (dimensione "Calm"). | [arXiv:1010.3003](https://arxiv.org/abs/1010.3003) | VERIFICATA |
| ↳ **Critica**: Lachanski, Pav (2017), "Shy of the Character Limit: 'Twitter Mood Predicts the Stock Market' Revisited", *Econ Journal Watch* 14(3):302-345 | Il risultato non si replica: l'effetto esiste solo nel sottocampione originale, il che è compatibile con data snooping. Fuori campione non c'è predittività. Il fondo nato sull'idea (Derwent Capital) ha chiuso nel 2012. | [EJW](https://econjwatch.org/articles/shy-of-the-character-limit-twitter-mood-predicts-the-stock-market-revisited) | VERIFICATA |
| Baker, Wurgler (2006), "Investor Sentiment and the Cross-Section of Stock Returns", *JF* 61(4):1645-1680 | Quando il sentiment aggregato è alto, i titoli piccoli, giovani, volatili, non profittevoli e speculativi rendono **meno** in seguito; quando è basso, rendono di più. Il sentiment è un predittore *contrarian* sui titoli difficili da valutare. | [doi:10.1111/j.1540-6261.2006.00885.x](https://doi.org/10.1111/j.1540-6261.2006.00885.x) | VERIFICATA |
| Loughran, McDonald (2011), "When Is a Liability Not a Liability? Textual Analysis, Dictionaries, and 10-Ks", *JF* 66(1):35-65 | Quasi 3/4 delle parole "negative" del dizionario Harvard non sono negative in contesto finanziario. Gli autori propongono 6 liste di parole specifiche per la finanza (dizionario LM). | [doi:10.1111/j.1540-6261.2010.01625.x](https://doi.org/10.1111/j.1540-6261.2010.01625.x) · [SSRN 1331573](https://papers.ssrn.com/abstract=1331573) | VERIFICATA |
| Araci (2019), "FinBERT: Financial Sentiment Analysis with Pre-trained Language Models" | Un BERT adattato alla finanza raggiunge lo stato dell'arte su Financial PhraseBank e FiQA. | [arXiv:1908.10063](https://arxiv.org/abs/1908.10063) | VERIFICATA |
| Huang, Wang, Yang (2023), "FinBERT: A Large Language Model for Extracting Information from Financial Text", *Contemporary Accounting Research* 40(2):806-841 | Un FinBERT diverso da quello di Araci. Supera il dizionario LM e altri metodi ML sulle frasi dei report degli analisti, soprattutto con pochi dati etichettati. | [doi:10.1111/1911-3846.12832](https://doi.org/10.1111/1911-3846.12832) | VERIFICATA |
| Lopez-Lira, Tang (2023-2025), "Can ChatGPT Forecast Stock Price Movements? Return Predictability and Large Language Models" | Lo score di ChatGPT sui titoli di news predice il rendimento del giorno dopo, e GPT-4 fa meglio dei modelli più piccoli (BERT e GPT-2 no). L'effetto è più forte su small cap e news negative, e **cala con l'adozione degli LLM** (più efficienza). | [arXiv:2304.07619](https://arxiv.org/abs/2304.07619) · [SSRN 4412788](https://doi.org/10.2139/ssrn.4412788) | VERIFICATA |
| ↳ **Critica / look-ahead**: Lopez-Lira, Tang, Zhu (2025), "The Memorization Problem: Can We Trust LLMs' Economic Forecasts?" | Gli LLM hanno memorizzato dati economici (livelli degli indici e altro) prima del cutoff. I test pre-cutoff non distinguono abilità da memoria; dopo il cutoff il recall sparisce. | [arXiv:2504.14765](https://arxiv.org/abs/2504.14765) | VERIFICATA |
| ↳ Gao, Jiang, Yan (2025/2026), "A Test of Lookahead Bias in LLM Forecasts" (poi "Detecting...") | Propone un test statistico per il bias: la memorizzazione gonfia in modo sostanziale la predittività apparente dei titoli di news sui rendimenti. | [arXiv:2512.23847](https://arxiv.org/abs/2512.23847) | VERIFICATA |
| Da, Engelberg, Gao (2011), "In Search of Attention", *JF* 66(5):1461-1499 | Il Google Search Volume Index misura l'attenzione retail. Un aumento dell'SVI predice prezzi più alti nelle 2 settimane successive, con **inversione** entro l'anno. Contribuisce anche al first-day return delle IPO e al loro underperformance di lungo periodo. | [doi:10.1111/j.1540-6261.2011.01679.x](https://doi.org/10.1111/j.1540-6261.2011.01679.x) | VERIFICATA (rivista, volume e pagine da 2 fonti; DOI da 1 fonte) |
| Bradley, Hanousek, Jame, Xiao (2024), "Place Your Bets? The Value of Investment Research on Reddit's Wallstreetbets", *RFS* 37(5):1409-1459 | Prima di GameStop (gen. 2021) le "due diligence" su WSB predicevano rendimenti e notizie sui cash flow; **dopo GME la predittività scompare**, perché i post diventano più orientati a hype e price pressure. | [doi:10.1093/rfs/hhad098](https://doi.org/10.1093/rfs/hhad098) | VERIFICATA |
| Barber, Huang, Odean, Schwarz (2022), "Attention-Induced Trading and Returns: Evidence from Robinhood Users", *JF* 77(6):3141-3190 | Gli utenti Robinhood fanno herding sui titoli ad alta attenzione. I titoli più comprati in un giorno rendono in media **−4,7% a 20 giorni** (−19,6% negli eventi di herding estremo). | [doi:10.1111/jofi.13183](https://doi.org/10.1111/jofi.13183) | VERIFICATA |

### 2.4 Retail, day trading e costi

| Paper | Risultato principale | Link | Stato |
|---|---|---|---|
| Barber, Odean (2000), "Trading Is Hazardous to Your Wealth", *JF* 55(2):773-806 | Su 66.465 famiglie (1991-96), i trader più attivi rendono l'11,4% annuo contro il 17,9% del mercato. Più si scambia, peggio va, e la causa è l'overconfidence. | [doi:10.1111/0022-1082.00226](https://doi.org/10.1111/0022-1082.00226) | VERIFICATA |
| Barber, Lee, Liu, Odean (2014), "The cross-section of speculator skill: Evidence from day trading", *J. Financial Markets* 18:1-24 | Su Taiwan 1992-2006, **meno dell'1%** dei day trader guadagna in modo prevedibile e persistente al netto delle commissioni. I peggiori perdono circa 29 bps al giorno dopo le fee. | [doi:10.1016/j.finmar.2013.05.006](https://doi.org/10.1016/j.finmar.2013.05.006) | VERIFICATA |
| Chague, De-Losso, Giovannetti (2019/2020), "Day Trading for a Living?" | Brasile, futures su mini-indice, 2013-2015: tra chi persiste oltre 300 giorni, il **97% perde**, solo l'1,1% guadagna più del salario minimo e non c'è evidenza di apprendimento. | [SSRN 3423101](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3423101) | VERIFICATA |
| Novy-Marx, Velikov (2016) | Vedi §2.1: i costi di transazione eliminano le anomalie ad alto turnover. | [doi:10.1093/rfs/hhv063](https://doi.org/10.1093/rfs/hhv063) | VERIFICATA |

### 2.5 Rischio e sizing

| Paper | Risultato principale | Link | Stato |
|---|---|---|---|
| Kelly (1956), "A New Interpretation of Information Rate", *Bell System Technical Journal* 35(4):917-926 | Massimizzare E[log ricchezza] massimizza il tasso di crescita asintotico; la frazione ottima per una scommessa binaria è f* = p − q/b. | [doi:10.1002/j.1538-7305.1956.tb03809.x](https://doi.org/10.1002/j.1538-7305.1956.tb03809.x) · [archive.org scan](https://archive.org/details/bstj35-4-917) | VERIFICATA (DOI da 1 fonte aggregata, scan su archive.org) |
| Thorp (2006), "The Kelly Criterion in Blackjack, Sports Betting and the Stock Market" | Vedi §1.3. | [PDF](https://www.Gwern.net/doc/statistics/decision/2006-thorp.pdf) | VERIFICATA |
| MacLean, Thorp, Ziemba (2010), "Long-term capital growth: the good and bad properties of the Kelly and fractional Kelly capital growth criteria", *Quantitative Finance* 10(7):681-687 | Il Kelly massimizza la crescita ma con puntate molto grandi e drawdown pesanti nel breve periodo. Il **Kelly frazionario** (f · Kelly + resto in cash) scambia crescita con sicurezza. | [doi:10.1080/14697688.2010.506108](https://doi.org/10.1080/14697688.2010.506108) · [PDF Berkeley](https://www.stat.berkeley.edu/~aldous/157/Papers/Good_Bad_Kelly.pdf) | VERIFICATA |
| Moreira, Muir (2017), "Volatility-Managed Portfolios", *JF* 72(4):1611-1644 | Scalare l'esposizione per 1/varianza realizzata del mese precedente produce alpha positivi su mercato, value, momentum e altri fattori. Si riduce il rischio quando la vol è alta. | [doi:10.1111/jofi.12513](https://doi.org/10.1111/jofi.12513) | VERIFICATA |
| ↳ **Critica**: Cederburg, O'Doherty, Wang, Yan (2020), "On the performance of volatility-managed portfolios", *JFE* 138(1):95-117 | Su 103 strategie, la versione vol-managed **non batte sistematicamente** l'originale in tempo reale e fuori campione; le regressioni di spanning sono instabili. | [doi:10.1016/j.jfineco.2020.04.015](https://doi.org/10.1016/j.jfineco.2020.04.015) | VERIFICATA |

### 2.6 Replica degli investitori top

| Paper | Risultato principale | Link | Stato |
|---|---|---|---|
| Frazzini, Kabiller, Pedersen (2018), "Buffett's Alpha", *Financial Analysts Journal* 74(4):35-55 | L'alpha di Berkshire diventa non significativo controllando per BAB (betting-against-beta) e QMJ (quality-minus-junk), con una leva di circa 1,7x. Buffett è replicabile come **fattori** (titoli sicuri, economici, di qualità, con leva), non come singole scelte. | [SSRN 3197185](https://papers.ssrn.com/abstract=3197185) · [NBER w19681](https://www.nber.org/papers/w19681.pdf) | VERIFICATA |
| Cohen, Polk, Silli (2010), "Best Ideas" (WP LSE/FMG DP624) | Le posizioni a massima convinzione dei gestori (maggiore sovrappeso rispetto al mercato) sovraperformano di circa 1-2,5% a trimestre; il resto del portafoglio è diluizione. | [PDF LSE](https://personal.lse.ac.uk/polk/research/BestIdeas.pdf) · [LSE Research Online](https://researchonline.lse.ac.uk/id/eprint/24471) | VERIFICATA (WP; stato di pubblicazione non verificato) |
| Eggers, Hainmueller (2013), "Capitol Losses: The Mediocre Performance of Congressional Stock Portfolios", *J. of Politics* 75(2):535-551 | Nel 2004-2008 il membro medio del Congresso USA ha **sottoperformato** il mercato del 2-3% annuo. Copiare i politici non è la miniera d'oro che si racconta. | [doi:10.1017/S0022381613000194](https://doi.org/10.1017/S0022381613000194) · [PDF MIT](https://www.mit.edu/~jhainm/Paper/CL.pdf) | VERIFICATA |
| Brown, Schwarz (circa 2013-14), studio sul cloning da 13F | Secondo la citazione FT, **nessuna evidenza** che le strategie copycat basate sui 13F diano benefici all'investitore di lungo periodo; i 13F arrivano fino a 45 giorni dopo la fine del trimestre. | [NYU Stern news](https://www.stern.nyu.edu/experience-stern/news/stephen-brown-ft-1-14.md) | PARZIALE (solo fonte secondaria; titolo esatto del paper non verificato) |

---

## 3. Stato dell'arte 2024-2026: agenti LLM per il trading

### 3.1 Framework principali

| Sistema | Cosa fa | Link | Stato |
|---|---|---|---|
| **FinGPT** (Yang, Liu, Wang, 2023) | Un framework open-source data-centric: pipeline di raccolta dati finanziari e fine-tuning LoRA a basso costo di LLM open, con task di sentiment, robo-advisor e segnali. | [arXiv:2306.06031](https://arxiv.org/abs/2306.06031) | VERIFICATA |
| **FinMem** (Yu et al., 2023; ICLR 2024 workshop, AAAI-SS, IEEE TBD 2025) | Un agente singolo con memoria stratificata (breve, medio e lungo termine) e un "profilo caratteriale" (propensione al rischio). Viene testato su pochi titoli e in finestre brevi. | [arXiv:2311.13743](https://arxiv.org/abs/2311.13743) | VERIFICATA |
| **TradingAgents** (Xiao, Sun, Luo, Wang, dic. 2024) | Un'organizzazione multi-agente che imita un trading desk: 4 analisti (tecnico, social, news, fondamentali), dibattito tra ricercatori Bull e Bear, trader e team di rischio. Riporta miglioramenti di rendimento cumulato, Sharpe e max drawdown, ma su pochi titoli e in una finestra di pochi mesi. | [arXiv:2412.20138](https://arxiv.org/abs/2412.20138) | VERIFICATA |
| **FinRL Contests 2023-2025** (incl. FinRL-DeepSeek) | Benchmark di agenti RL su ambienti di mercato paralleli su GPU. Il track 2025 integra nel RL segnali LLM (sentiment e livello di rischio dalle news). | [arXiv:2504.02281](https://arxiv.org/abs/2504.02281) · [FinRL-DeepSeek arXiv:2502.07393](https://arxiv.org/abs/2502.07393) | VERIFICATA (esistenza); i risultati dei vincitori non sono verificati |

### 3.2 Evidenze critiche: backtest e realtà

| Studio | Evidenza | Link | Stato |
|---|---|---|---|
| **FINSABER**, Li, Kim, Cucuringu, Ma (2025-2026), "Can LLM-based Financial Investing Strategies Outperform the Market in Long Run?" | Con backtest di 20 anni, un universo ampio e la mitigazione dei bias, i vantaggi degli agenti LLM riportati in letteratura **si riducono o spariscono**. Gli agenti sono troppo conservativi nei bull market (sotto il buy&hold) e troppo aggressivi nei bear market. | [arXiv:2505.07078](https://arxiv.org/abs/2505.07078) | VERIFICATA |
| **StockBench** (Chen, Yao et al., ott. 2025) | Test senza contaminazione (dati del 2025): gli agenti faticano a battere in modo consistente l'equal-weight buy&hold. Ad esempio il migliore (Kimi-K2) fa +1,9% contro +0,4% del benchmark, su pochi mesi e **senza costi di transazione**. Sono sensibili al regime. | [arXiv:2510.02209](https://arxiv.org/abs/2510.02209) | VERIFICATA |
| **LiveTradeBench** (nov. 2025) | 50 giorni live, 21 LLM, su azioni USA e Polymarket. Il punteggio LMArena **non predice** i rendimenti di trading, e la performance su un mercato non si trasferisce all'altro. | [arXiv:2511.03628](https://arxiv.org/abs/2511.03628) | VERIFICATA |
| **Agent Market Arena** (ott. 2025), "When Agents Trade: Live Multi-Market Trading Benchmark for LLM Agents" | Benchmark live su crypto e azioni: le differenze dipendono più dal *framework* dell'agente che dal modello di base. | [arXiv:2510.11695](https://arxiv.org/abs/2510.11695) | VERIFICATA |
| **Nof1 Alpha Arena Season 1** (18 ott. - 3 nov. 2025) | 6 LLM con 10.000 $ ciascuno su perpetual crypto (Hyperliquid). Qwen3-Max fa circa +22%, DeepSeek circa +5%, GPT-5 circa −62% e Gemini 2.5 Pro circa −57%; 4 modelli su 6 in perdita. Gli stessi organizzatori la definiscono esplorativa e non statisticamente significativa (un solo run, 2 settimane, alta leva). | [Decrypt](https://decrypt.co/345006/ai-crypto-trading-showdown-deepseek-grok-winning-gemini-implodes) · [datawallet](https://www.datawallet.com/crypto/alpha-arena-nof1-ai-explained) | VERIFICATA (fonti giornalistiche, nessun paper) |
| **Look-ahead bias negli LLM**: Lopez-Lira, Tang, Zhu (2025); Gao, Jiang, Yan (2025); FinCAD (2026, arXiv:2605.24564) | Ogni backtest LLM su date precedenti al cutoff di addestramento è contaminato da memorizzazione. FinCAD riduce fino al 67% i rendimenti in-sample "memorizzati", mentre l'OOS 2025 resta invariato. | [2504.14765](https://arxiv.org/abs/2504.14765) · [2512.23847](https://arxiv.org/abs/2512.23847) · [2605.24564](https://arxiv.org/abs/2605.24564) | VERIFICATA (abstract) |

**Giudizio complessivo sullo stato dell'arte:**
1. Quasi tutti i risultati positivi degli agenti LLM vengono da backtest brevi (mesi), su pochi titoli large-cap, dentro il periodo di addestramento del modello e senza costi. Ciascuna di queste caratteristiche basta a gonfiare i numeri.
2. I benchmark live o post-cutoff del 2025-2026 (StockBench, LiveTradeBench, AMA, Alpha Arena) mostrano risultati vicini al buy&hold, con alta varianza tra i modelli e nessuna relazione stabile tra "intelligenza" generale e P&L.
3. Il valore più solido degli LLM resta **l'estrazione di informazione dal testo** (sentiment e classificazione delle news, alla Lopez-Lira & Tang o FinBERT), usata come *feature* dentro un modello quantitativo con validazione rigorosa, non come decisore autonomo. Anche quell'edge si sta erodendo con l'adozione.

---

## 4. Sintesi per il progetto

### 4.1 Le 10 lezioni che la letteratura impone

1. **Il benchmark è il buy&hold indicizzato al netto dei costi.** La maggior parte dei retail attivi sottoperforma (Barber-Odean 2000), meno dell'1% dei day trader ha abilità persistente (Barber et al. 2014) e il 97% dei day trader brasiliani perde (Chague et al.). Ogni strategia deve dimostrare di battere un ETF globale al netto di *tutti* i costi, altrimenti si investe passivo.
2. **Con 50 € i costi sono il fattore dominante.** Una commissione di 1 € è il 2% per operazione, quindi il 4% per un round-trip. Le anomalie ad alto turnover muoiono già con i costi istituzionali (Novy-Marx-Velikov 2016). Conseguenze: preferire broker o exchange con fee percentuali basse e frazioni di azioni, una frequenza bassa (settimanale o mensile) e strategie a basso turnover. Le "micro-transazioni" frequenti sono quasi certamente a valore atteso negativo.
3. **Le anomalie pubblicate si degradano.** In media perdono circa la metà dopo la pubblicazione (McLean-Pontiff), e una quota rilevante non si replica (HXZ 2020; dibattito con JKP 2023). Bisogna aspettarsi in produzione circa il 50% del rendimento del paper e privilegiare i fattori robusti e replicati: momentum, value, quality/profitability, low-risk.
4. **La soglia di significatività è t > 3, non 2** (Harvey-Liu-Zhu). Con molte prove serve correggere: Deflated Sharpe Ratio e PBO/CSCV (Bailey-López de Prado) sono obbligatori nella pipeline. Va registrato **ogni** tentativo, per contare il numero di trial.
5. **La validazione deve essere temporale e senza leakage.** Servono purged/embargoed CV, walk-forward e combinatorial purged CV (López de Prado, AFML), oltre a un hold-out finale mai toccato. Niente CV k-fold standard.
6. **Il ML aiuta, ma con segnali piccoli.** L'R² OOS mensile realistico è inferiore all'1% (Gu-Kelly-Xiu), e i gradient boosted tree battono le reti profonde e i foundation model zero-shot sui rendimenti (Re(Visiting) TSFM 2025). Va partito da LightGBM/CatBoost con feature note; i TSFM servono al massimo per previsioni di volatilità o volume.
7. **Il sentiment è soprattutto un segnale contrarian o di breve periodo, e si erode.** Il pessimismo dei media si inverte (Tetlock), l'attenzione retail porta rendimenti negativi a 20 giorni (Robinhood) e un pump di 2 settimane seguito da inversione (Google SVI), il sentiment aggregato predice al contrario i titoli speculativi (Baker-Wurgler), WSB ha perso valore dopo GME. I risultati alla Bollen sul "mood" non si replicano. Va usato il sentiment per **evitare** l'hype o fare contrarian sul crowding, non per inseguirlo.
8. **Gli LLM vanno usati come estrattori di feature, non come trader autonomi, e i backtest su dati pre-cutoff non valgono.** La memorizzazione invalida i test pre-cutoff (Lopez-Lira-Tang-Zhu 2025, Gao et al.), e i benchmark live mostrano risultati vicini al buy&hold (StockBench, LiveTradeBench, FINSABER, Alpha Arena). Ogni test di un segnale LLM va fatto solo su dati **successivi** al cutoff del modello usato, o in paper trading live.
9. **Il sizing conta quanto il segnale.** Il Kelly pieno è ottimo solo asintoticamente e con un edge noto; con un edge stimato con errore porta a drawdown rovinosi. Va usato un **Kelly frazionario** (1/4-1/2), con stima dell'edge "shrinkata" verso zero (MacLean-Thorp-Ziemba). Il volatility targeting riduce il rischio di coda, ma il suo alpha fuori campione è incerto (Moreira-Muir contro Cederburg et al.). Va usato per **controllare il rischio**, non come fonte di rendimento. Per l'allocazione tra asset, il naive 1/N batte l'ottimizzazione media-varianza stimata (DeMiguel et al.).
10. **"Replicare i top investor" significa replicare i loro fattori, non i loro trade.** L'alpha di Buffett si spiega con value + quality + low-beta + leva (Frazzini et al.). I 13F arrivano fino a 45 giorni dopo la fine del trimestre e il cloning ha evidenza mista; i politici USA in media sottoperformano (Eggers-Hainmueller). L'unico segnale di replica con supporto accademico è il "best ideas" (posizioni ad alta convinzione), ma con ritardo e su dati 13F.

### 4.2 Strategie candidate con evidenze

Le strategie sono ordinate dalla più robusta alla più speculativa. Il capitale di 50 € impone frequenza bassa, frazioni di ETF o azioni e costi percentuali.

| # | Strategia | Evidenza a supporto | Rischi e note per 50 € | Priorità |
|---|---|---|---|---|
| A | **Core passivo + piano di accumulo** (ETF azionario globale, eventuale quota obbligazionaria) | Malkiel, Bogle, Barber-Odean | È il benchmark e la "parte sicura". Ogni strategia attiva gestisce solo una quota satellite. | Baseline obbligatoria |
| B | **Time-series momentum / trend following su pochi ETF multi-asset** (azioni, bond, oro, commodity), ribilanciato mensilmente, con volatility targeting | Moskowitz-Ooi-Pedersen 2012; AMP 2013; Moreira-Muir 2017 | Turnover basso. La crescita del trend-following dipende in larga parte dal vol-scaling. Ha lunghi periodi piatti (ad esempio 2010-2019 per i CTA). | Alta |
| C | **Rotazione momentum cross-section tra ETF settoriali o paese**, mensile, eventualmente combinata con value | Jegadeesh-Titman 1993; AMP 2013 (value e momentum correlati negativamente) | È soggetta a momentum crash (2009). Servono un filtro di regime e un limite al turnover. | Alta |
| D | **Tilt fattoriale "Buffett-like"** (quality + value + low-vol) tramite ETF fattoriali o screening su poche azioni frazionate | Frazzini et al. 2018; Fama-French 2015 (RMW); Novy-Marx-Velikov (basso turnover) | È la vera "replica dei top investor". Un premio piccolo e lento richiede pazienza. | Media-alta |
| E | **Overlay di sentiment contrarian / filtro anti-hype**: non comprare (o ridurre) i titoli con picchi di attenzione (Google Trends, Reddit, menzioni social) | Da-Engelberg-Gao 2011; Barber et al. 2022 (Robinhood −4,7% a 20 giorni); Baker-Wurgler 2006 | Va usato come **filtro di rischio**, non come strategia autonoma: andare short su meme stock è pericoloso (squeeze). | Media |
| F | **Score di news da LLM come feature** (alla Lopez-Lira & Tang), dentro un modello GBM | Lopez-Lira-Tang 2023-25; Huang-Wang-Yang 2023 (FinBERT) | Edge in erosione, più forte sulle small cap (poco liquide). Va testato solo dopo il cutoff del modello o in paper trading. Il costo API va confrontato col capitale. | Media, solo sperimentale |
| G | **Indice di "narrazione/fede" per asset** (viralità dei temi, alla Shiller) come variabile di regime | Shiller 2019 (teoria); Tetlock 2007 (media); Bradley et al. 2024 (WSB) | Scarsa evidenza quantitativa diretta, quindi è area di ricerca. È utile per la gestione del rischio (bolle, crowding) più che per l'alpha. | Esplorativa |
| H | **Mean reversion / pair trading** su coppie cointegrate di ETF | Chan 2013 | Turnover più alto: i costi la uccidono con 50 €. Ha senso solo se l'exchange ha fee vicine a zero. | Bassa |
| I | **Agente LLM autonomo che decide i trade** | TradingAgents, FinMem (risultati in backtest) contro FINSABER, StockBench, LiveTradeBench, Alpha Arena (risultati live) | Non c'è evidenza robusta di sovraperformance netta. Ha senso solo come laboratorio in paper trading, mai con capitale reale all'inizio. | Da evitare in produzione |
| J | **Day trading intraday / scalping a micro-transazioni** | Barber et al. 2014; Chague et al. 2020 | Evidenza fortemente negativa per i retail; con 50 € i costi fissi la rendono quasi certamente perdente. | Da escludere |

### 4.3 Protocollo di validazione minimo (dalla letteratura)

1. Dati point-in-time, senza survivorship bias, con costi realistici (commissione minima, spread, slippage, cambio valuta).
2. Registro di tutti i trial, per calcolare DSR e PBO.
3. Walk-forward con purged/embargoed CV; hold-out finale toccato una sola volta.
4. Soglia: t-stat > 3 oppure DSR > 0,95 e PBO < 0,2. Le soglie su DSR e PBO sono indicative e vanno fissate dal progetto.
5. Confronto contro buy&hold e 1/N, al netto dei costi.
6. Almeno 3-6 mesi di paper trading live prima del capitale reale. Per i segnali LLM conta solo il periodo successivo al cutoff del modello.
7. Kelly frazionario ≤ 1/2, kill-switch sul drawdown, nessuna leva.

---

## Appendice: elementi non verificati o da ricontrollare

- Anno esatto della 3ª ed. di *Inside the Black Box* (Narang): circa 2024, non confermato.
- Anni 2007 e 2017 di *The Little Book of Common Sense Investing* (Bogle): confermato solo che l'editore è Wiley.
- *The Black Swan* (Taleb, Random House 2007): non confermato da una ricerca dedicata in questa sessione, anche se è un dato bibliografico noto.
- Cifre esatte di McLean-Pontiff (26%/58%) e R² di Gu-Kelly-Xiu: da ricontrollare sul full text.
- Paper Brown-Schwarz sul cloning da 13F: titolo esatto non trovato.
- Schroeder-Posch (2024), "Outperforming the Market: Portfolio Strategy Cloning from SEC 13F Filings": fonti in conflitto sui risultati, **non usare** senza leggere il paper.
- Risultati dei vincitori dei FinRL Contest: non verificati.
