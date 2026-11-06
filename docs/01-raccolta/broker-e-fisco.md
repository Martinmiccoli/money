# Broker e fisco: ricerca per il trading algoritmico (Italia)

**Data della ricerca:** 2026-11-06
**Profilo:** persona fisica residente in Italia, lavoratore dipendente, capitale iniziale 50 €, nessun adempimento fiscale (quindi **regime amministrato**), budget per i servizi 0 €, prima paper trading e poi soldi veri.

> **Legenda affidabilità**
> - ✅ **VERIFICATO**: confermato da fonte ufficiale (broker, Agenzia delle Entrate, testo normativo) o da più fonti indipendenti coerenti, con URL.
> - 🟡 **PROBABILE**: riportato da fonti secondarie (stampa specializzata, comparatori) coerenti tra loro, ma senza riscontro su una pagina ufficiale.
> - ❌ **INCERTO**: fonti discordanti, datate o assenti. **Da verificare prima di decidere.**
>
> Le commissioni cambiano spesso. Prima di aprire un conto controlla sempre il foglio informativo o il listino ufficiale. Alcuni siti ufficiali (Interactive Brokers, Trade Republic, Directa) non si sono lasciati leggere in automatico (errori 403/404): per quei broker i dati vengono da snippet delle pagine ufficiali o da fonti secondarie, e lo segnalo.
>
> Questo documento non è consulenza fiscale.

---

## 0. Sintesi in una tabella

| Broker | Regime amministrato | API ufficiale di trading | Paper/demo | Frazioni | Costo tipico per ordine piccolo |
|---|---|---|---|---|---|
| **Trade Republic** | ✅ Sì (dal 30/01/2025, IBAN IT) | ❌ No (solo librerie non ufficiali, es. `pytr`) | No | 🟡 Sì, da 1 € | 1 € fisso |
| **Scalable Capital** | ✅ Sì (dal 01/09/2026, filiale IT) | ❌ No | No | 🟡 Sì (nei piani d'accumulo, da 1 €) | 0,99 € (FREE) |
| **Saxo Italia (ex BG Saxo)** | 🟡 Sì (Saxo SIM S.p.A.) | ✅ OpenAPI REST + streaming | ✅ SIM gratuito | ❌ Non verificato | 1 USD (azioni USA), 2 € (azioni IT) |
| **Directa SIM** | 🟡 Sì (SIM italiana) | ✅ dAPI via socket TCP locale (Darwin) | ❌ Nessun conto di prova per l'API | No | 0,19%, min 1,5 € (IT); circa 9 $ (USA) ❌ |
| **Fineco** | 🟡 Sì (banca italiana) | ❌ Nessuna API pubblica trovata | No | 🟡 No | 0,19%, min 2,95 € |
| **Webank / Banca Sella / isybank** | 🟡 Sì (banche italiane) | ❌ No (le API di Sella/Fabrick riguardano i pagamenti) | No | ❌ Non trovato | Webank 2,75–12 €; Sella circa 8 € |
| **Interactive Brokers** | ❌ No (dichiarativo) | ✅ TWS API, Web API (REST/WS), FIX | ✅ Sì | ✅ Sì | US: 0,005 $/azione, min 1 $, max 1% del controvalore |
| **Alpaca** | ❌ No (broker USA) | ✅ REST + WebSocket | ✅ Gratis per chiunque, basta un'email | ✅ Sì | 0 commissioni (USA) |
| **eToro** | ❌ No (dichiarativo, eToro Europe, Cipro) | 🟡 Public API (beta, rilascio graduale) | ✅ Demo | ✅ Sì | 0 / 1–2 $ ❌ + cambio 0,75–1,5% |
| **DEGIRO** | ❌ No (dichiarativo) | ❌ No (solo API non ufficiali) | No | No | circa 2 € (1 € + 1 € di gestione) 🟡 |
| **Trading 212** | ❌ No (dichiarativo, Cipro) | ✅ API v0 (beta), REST | ✅ Demo + API demo | ✅ Sì | 0 commissioni + 0,15% di cambio |
| **Freedom24** | ❌ No (dichiarativo) | 🟡 API Tradernet (documentata da SDK di terzi) | ❌ Non verificato | ❌ | variabile/promo ❌ |
| **XTB** | ❌ No (dichiarativo) 🟡 | ❌ Non verificato | Demo | Sì | — |
| **Revolut** | ❌ No sugli investimenti (dichiarativo) 🟡 | No | No | Sì | — |
| **Lightyear** | ❌ Nessuna evidenza di amministrato | No | No | Sì | — |

**In breve:** solo **Directa** e **Saxo Italia** combinano regime amministrato e API ufficiale di trading. Trade Republic e Scalable hanno amministrato e frazioni a circa 1 €, ma nessuna API. I broker con le API migliori (IBKR, Alpaca, Trading 212) sono tutti in **regime dichiarativo**.

---

## 1. Broker: dettaglio

### 1.1 Trade Republic
| Voce | Dato | Stato |
|---|---|---|
| Regime amministrato | Sì, dal 30 gennaio 2025 con la succursale italiana e l'IBAN italiano. I nuovi clienti sono automaticamente in amministrato. | ✅ [Teleborsa](https://www.teleborsa.it/News/2025/01/30/trade-republic-lancia-succursale-in-italia-e-iban-sara-sostituto-d-imposta-per-investimenti-3.html), [Il Sole 24 Ore](https://en.ilsole24ore.com/art/trade-republic-conto-corrente-iban-e-regime-amministrato-anche-italia-AGCSh2ZC), [comunicato ufficiale (PDF)](https://assets.traderepublic.com/assets/files/250130_TradeRepublic_PressRelease_BranchLaunch-Italy_IT_IT.pdf) |
| Amministrato anche sulle crypto | Lo dicono alcune fonti (Rankia), un'altra (MySolution, 07/2026) lo smentisce | ❌ INCERTO: [Rankia](https://rankia.it/trade-republic-sostituto-dimposta/), [MySolution](https://www.mysolution.it/fisco/informazioni/news/2026/07/08/trade-republic-regime-amministrato-o-dichiarativo/) |
| API ufficiale | **No.** Esistono solo librerie reverse-engineered (`pytr`, `trade-republic` su PyPI) che usano l'API privata dell'app e richiedono di "accoppiare" un dispositivo, scollegando lo smartphone. | ✅ nessuna API ufficiale trovata. ⚠️ **Rischio ToS**: [pytr](https://github.com/nborrmann/pytr) |
| Paper/demo | No | 🟡 |
| Frazioni | Sì: ordini in importo da 1 €, eseguiti a mercato su LS Exchange (niente ordini limite sulle frazioni) | 🟡 [promarketer](https://www.promarketer.it/investimenti/broker/trade-republic/trade-republic-azioni-frazionate/), [Rankia](https://rankia.it/recensione-di-trade-republic-pro-e-contro-regolamento-prodotti-e-commissione/) |
| Mercati | Azioni ed ETF (UE e USA tramite LS Exchange), obbligazioni, crypto, derivati | 🟡 |
| Commissioni | **1 € fisso per ordine** (azioni, ETF, crypto, obbligazioni). Piani d'accumulo gratuiti. Spread incluso nel prezzo. | 🟡 più fonti concordi; listino ufficiale non leggibile in automatico |
| Deposito minimo | Nessuno | 🟡 |

### 1.2 Scalable Capital
| Voce | Dato | Stato |
|---|---|---|
| Regime amministrato | **Sì, dal 1° settembre 2026** (succursale di Milano e IBAN italiano). È facoltativo: si può restare in dichiarativo. Per i vecchi clienti decorre dal trasferimento effettivo alla filiale, senza effetto retroattivo. | ✅ [Newsroom Scalable](https://it.scalable.capital/en/newsroom/italy-bank-branch), [Help Scalable](https://help.scalable.capital/en/italian-branch-0e68dfd5/taxes-7d44a39c/do-i-still-need-to-file-my-taxes-for-2026-even-if-i-cho-ee21cb3d), [Teleborsa](https://www.teleborsa.it/News/2026/09/01/scalable-capital-lancia-iban-italiano-e-regime-amministrato-saldutti-vogliamo-restare-per-decenni-1.html) |
| API ufficiale | No | 🟡 |
| Paper | No | 🟡 |
| Frazioni | Nei piani d'accumulo (da 1 €). Per gli ordini singoli non è verificato. | 🟡 |
| Crypto | Solo tramite ETP/ETN quotati (niente crypto "vere") | 🟡 [Rankia](https://rankia.it/brokers/trade-republic-vs-scalable-capital-quale-broker-e-il-migliore) |
| Commissioni | FREE: **0,99 €** per ordine. PRIME+: 4,99 €/mese (0 € sopra i 250 €, sotto resta 0,99 €). Piani d'accumulo gratuiti da 1 €. | ✅ PRIME+ dalla [newsroom ufficiale](https://it.scalable.capital/en/newsroom/italy-bank-branch); 🟡 FREE |
| Deposito minimo | Nessuno | 🟡 |

### 1.3 Saxo Italia (ex BG Saxo, Saxo SIM S.p.A.)
| Voce | Dato | Stato |
|---|---|---|
| Regime amministrato | Sì, gestito internamente da Saxo SIM (il "zainetto fiscale" resta invariato dopo il rebranding) | 🟡 [RisparmiOggi](https://www.risparmioggi.it/bg-saxo-diventa-saxo-cosa-cambia-per-vecchi-e-nuovi-clienti/) |
| API ufficiale | **OpenAPI** (REST + streaming WebSocket). Ambiente **SIM gratuito** con token di 24 h dal portale sviluppatori. In live, i "direct retail clients" di Saxo Group possono chiedere le credenziali: serve un conto live finanziato e almeno un'app SIM; l'approvazione è di solito automatica. Qualunque linguaggio (HTTP), esiste un SDK Python della community (`saxo_openapi`). | ✅ [developer.saxo – live credentials](https://developer.saxo/openapi/learn/direct-clients-request-for-openapi-application-credentials-for-the-live-environ), [developer.saxo](https://developer.saxo/openapi) |
| L'OpenAPI live vale anche per i clienti di Saxo **Italia**? | Non confermato esplicitamente | ❌ **INCERTO: chiedere a Saxo Italia** |
| Paper | Sì, ambiente SIM gratuito (vale anche come demo di piattaforma) | ✅ |
| Frazioni | Non trovato | ❌ |
| Commissioni | Azioni USA **1 USD** per ordini sotto 50.000 $. Azioni Italia **2 €** per ordini sotto 50.000 €. Cambio valuta circa 0,25%. | 🟡 (snippet della pagina Saxo IT e [Rankia](https://rankia.it/recensione-e-opinioni-saxo-bank)) |
| Dati di mercato in tempo reale via API | Potrebbero richiedere abbonamenti per borsa | ❌ INCERTO |
| Deposito minimo | Non verificato | ❌ |

### 1.4 Directa SIM
| Voce | Dato | Stato |
|---|---|---|
| Regime amministrato | Sì (SIM italiana, sostituto d'imposta) | 🟡 più fonti (es. [Rankia](https://rankia.it/analisi-di-directa-pro-e-contro-regolamento-prodotti-e-commissione/)) |
| API ufficiale | **dAPI**: socket TCP su `127.0.0.1` aperti dalla piattaforma Darwin (o da *Darwin Command Line*, senza interfaccia). Porte: 10001 prezzi, **10002 trading**, 10003 storico. Protocollo testuale (comandi `ACQAZ`, `VENAZ`, `ACQMARKET`, `REVORD`…), utilizzabile da qualunque linguaggio. | ✅ [Documentazione ufficiale dAPI](https://directa-it.github.io/documentation/en.html) |
| Costi API | Servizio di **trading via API gratuito**. **DATAFEED 20 €/mese**: i socket sono disponibili solo con il servizio prezzi attivo. Possibili esenzioni legate all'operatività non verificate. | ✅ (doc ufficiale) / ❌ esenzioni |
| Vincoli | Darwin deve girare con login attivo. Disconnessione automatica intorno a mezzanotte. Massimo 100 titoli sottoscrivibili. Login con OTP, quindi un'esecuzione 100% non presidiata è difficile (AutoLogin con dGO citato dalla doc). | ✅ / 🟡 |
| Paper | **Nessun conto di prova per sviluppare con l'API** | ✅ (doc ufficiale) |
| Frazioni | No | 🟡 |
| Commissioni | Azioni IT, profilo variabile: **0,19% (min 1,5 € – max 18 €)**. Profilo fisso circa 5 €. Azioni USA circa **9 $** per eseguito (fonti terze discordanti). Nessun canone sul conto. | 🟡 IT / ❌ USA |
| Deposito minimo | Nessuno (secondo fonti terze) | 🟡 |

### 1.5 Fineco
| Voce | Dato | Stato |
|---|---|---|
| Regime amministrato | Sì (banca italiana) | 🟡 |
| API | Nessuna API pubblica di trading trovata | 🟡 |
| Paper | No | 🟡 |
| Frazioni | No | 🟡 [BrokerChooser](https://brokerchooser.com/it/broker-reviews/fineco-bank-review) |
| Commissioni | Conto trading: **0,19%, min 2,95 € – max 19 €**. Under 30: 2,95 € (IT/UE), 3,95 $ (USA), con fonti non allineate. | 🟡 [Rankia](https://rankia.it/recensione-fineco-opinioni-sul-conto-trading) |

### 1.6 Webank, Banca Sella, isybank
| Voce | Dato | Stato |
|---|---|---|
| Regime amministrato | Webank: scelta tra amministrato e dichiarativo all'apertura. Sella e isybank: banche italiane. | 🟡 [Rankia Webank](https://rankia.it/recensione-di-webank-pro-e-contro-regolamento-prodotti-e-commissione) |
| API | No. Le API di Banca Sella (Fabrick) riguardano pagamenti e open banking, non il trading. | 🟡 |
| Commissioni | Webank: azioni IT da 12 € a 2,75 € (fisso, a scaglioni per volume). Sella: circa 8 € (piano fisso, fascia base). | 🟡 [BrokerChooser Sella](https://brokerchooser.com/it/broker-reviews/banca-sella-review) |
| isybank | Il sito ufficiale mostra solo **3 fondi comuni**; nessuna compravendita di singoli titoli trovata | 🟡 [isybank fondi](https://www.isybank.com/it/investimenti/fondi-comuni-investimento.html) |
| Giudizio | Non adatti: commissioni minime troppo alte per ordini da 5–50 € e nessuna API | — |

### 1.7 Interactive Brokers (IBKR Ireland)
| Voce | Dato | Stato |
|---|---|---|
| Regime amministrato | **No**: regime dichiarativo (quadri RT, RW, IVAFE a carico del cliente) | 🟡 più fonti, es. [MoneyViz](https://blog.moneyviz.it/come-pagare-le-tasse-su-interactive-brokers-guida-completa/) |
| API | ✅ **TWS API** (socket, con TWS/IB Gateway in esecuzione; Python, Java, C++, C#), **Web API** (REST + WebSocket), **FIX** (soprattutto istituzionale) | ✅ [TWS API docs](https://interactivebrokers.github.io/tws-api/introduction.html) |
| Paper | Sì, con 1.000.000 USD virtuali, collegato al conto reale. TWS e Web API funzionano anche in paper. | ✅ [IBKR – paper trading](https://www.interactivebrokers.com/docs/tws-api/doc/notes-limitations/limitations/paper-trading) |
| Frazioni | Sì: azioni USA da 1 $, azioni ed ETF europei senza minimo | ✅ [Finextra (annuncio IBKR)](https://finextra.com/pressarticle/92822/interactive-brokers-introduces-fractional-trading-in-european-stocks) |
| Commissioni | USA, Pro Fixed: **0,005 $/azione, min 1 $, max 1% del controvalore**. Su un ordine da 5 $ il tetto dell'1% scatta prima del minimo. Borse europee e frazioni UE: tiered 0,05%, min 1,25 € 🟡. Cambio valuta: commissione minima di circa 2 $ per conversione ❌. | ✅ [IBKR commissions](https://www.interactivebrokers.com/en/pricing/commissions-home.php) / 🟡 |
| Note | Ottimo per lo sviluppo, ma **incompatibile con "zero adempimenti"** | — |

### 1.8 Alpaca
| Voce | Dato | Stato |
|---|---|---|
| Regime amministrato | **No** (broker USA, nessuna stabile organizzazione in Italia) | ✅ (per definizione) |
| API | ✅ REST + WebSocket. SDK ufficiali in Python, JS, Go, C#. Azioni USA, opzioni, crypto. | ✅ [docs.alpaca.markets](https://docs.alpaca.markets/docs/paper-trading) |
| Paper | ✅ **"Anyone globally can create an Alpaca Paper Only Account"**: basta un'email, è gratis, 100k $ virtuali. Dati di mercato solo IEX; dividendi, slippage e fee regolamentari non simulati; crypto simulate. | ✅ [Alpaca Paper Trading](https://docs.alpaca.markets/docs/paper-trading) |
| Conto live per residenti in Italia | Non c'è una lista pubblica dei paesi. Alpaca Europe (ex WealthKernel) esiste dal 2026. | ❌ INCERTO: [Alpaca countries](https://alpaca.markets/support/countries-alpaca-is-available), [BusinessWire](https://www.businesswire.com/news/home/20260421441080/en/) |
| Frazioni / commissioni | Sì / 0 commissioni sulle azioni USA | 🟡 |

### 1.9 eToro
| Voce | Dato | Stato |
|---|---|---|
| Regime amministrato | **No**: eToro (Europe) Ltd, Cipro, regime dichiarativo | 🟡 [MoneyViz](https://blog.moneyviz.it/come-pagare-le-tasse-su-etoro-guida-completa/) |
| API | **Public API** (dati, ordini, social) sul [portale sviluppatori](https://api-portal.etoro.com/index.md). Dichiarata beta, rilascio graduale per mercati idonei, account verificato necessario. | ✅ esistenza / ❌ disponibilità in Italia |
| Demo | Sì (virtual portfolio) | 🟡 |
| Commissioni | Fonti discordanti: 0 € oppure 1–2 $ per trade dal 2026. Cambio 0,75–1,5%. Deposito minimo 50–200 $. | ❌ INCERTO |

### 1.10 DEGIRO
| Voce | Dato | Stato |
|---|---|---|
| Regime amministrato | **No** (dichiarativo) | 🟡 [MoneyViz](https://blog.moneyviz.it/come-pagare-le-tasse-su-degiro-guida-completa/) |
| API | **Nessuna API ufficiale.** Esistono solo API non ufficiali (es. `degiro-client`, DegiroAPI). ⚠️ Rischio ToS. | ✅ assenza |
| Commissioni | Circa 2 € (1 € + 1 € di gestione) su azioni IT e USA. 2,50 €/anno per ogni borsa estera. AutoFX 0,25%. | 🟡 |

### 1.11 Altri broker rilevanti
| Broker | Amministrato | API | Note | Stato |
|---|---|---|---|---|
| **Trading 212** | No (Trading 212 Markets Ltd, Cipro) | ✅ API v0 **beta**, REST. Ambiente demo `demo.trading212.com/api/v0` e live `live.trading212.com/api/v0`. Solo conti Invest/ISA. In live, secondo i risultati, solo ordini a mercato. Gli ordini a mercato **non sono idempotenti**. Limiti di frequenza per account. | 0 commissioni, cambio 0,15%, frazioni | ✅ [docs.trading212.com](https://docs.trading212.com/api) / 🟡 fisco [MoneyViz](https://blog.moneyviz.it/come-pagare-le-tasse-su-trading-212-guida-completa/) |
| **Freedom24** | No (dichiarativo) | API Tradernet (SDK di terzi su PyPI che rimandano a una doc ufficiale) | Promo a 0 commissioni fino al 31/08/2026, prelievo 7 € | 🟡 / ❌ |
| **XTB** | No (dichiarativo) | Non verificato | — | 🟡 [fiscoinvestimenti](https://fiscoinvestimenti.it/?p=9002) |
| **Revolut** | No sugli investimenti (Revolut Securities Europe UAB, Lituania) | No | — | 🟡 [MoneyViz](https://blog.moneyviz.it/come-pagare-le-tasse-su-revolut/) |
| **Lightyear** | Nessuna evidenza (Lightyear Europe AS, Estonia) | No | — | ❌ |

### 1.12 API non ufficiali: rischio
Esistono librerie reverse-engineered per **Trade Republic** (`pytr`, `trade-republic`) e **DEGIRO** (`degiro-client`, `DegiroAPI`). Problemi:
- probabile **violazione dei termini di servizio**, con rischio di blocco del conto;
- possono smettere di funzionare a ogni aggiornamento dell'app;
- richiedono di salvare PIN o credenziali in chiaro;
- `pytr` scollega lo smartphone durante l'accoppiamento.

**Raccomandazione: non usarle per inviare ordini reali.**

---

## 2. Crypto

### 2.1 Aliquote e regole 2026
| Voce | Regola | Stato / fonte |
|---|---|---|
| Aliquota plusvalenze crypto (art. 67 c.1 lett. c-sexies TUIR) | **33% dal 1° gennaio 2026**, introdotta dalla L. 207/2024 (legge di bilancio 2025). Era 26% nel 2025. | ✅ [Fiscal Focus](https://www.fiscal-focus.it/quotidiano/il-quotidiano/articoli-fisco/cripto-attivita-2026-aliquota-al-33-ma-scatta-una-deroga-per-i-token-di-moneta-elettronica-in-euro,3,180507), [centrofiscale](https://centrofiscale.com/regime-amministrato-dichiarativo-crypto-2027/), [Milano Finanza](https://www.milanofinanza.it/news/tasse-e-crypto-la-stagione-del-730-arriva-il-primo-exchange-italiano-che-paga-le-imposte-per-te-202605220957077101) |
| Deroga | **E-money token (EMT) in euro conformi a MiCAR: 26%**, introdotta dalla L. 199/2025 (legge di bilancio 2026). Le stablecoin in dollari restano al 33%. | 🟡 più fonti; comma esatto non verificato |
| Franchigia 2.000 € | **Abolita dal 2025** (L. 207/2024): si tassa dal primo euro | ✅ più fonti concordi |
| Minusvalenze crypto | Paniere **separato**: compensano solo plusvalenze crypto, con riporto fino al quarto periodo d'imposta successivo (art. 68 c. 9-bis TUIR). Le minusvalenze su azioni non compensano le crypto e viceversa. | 🟡 [MySolution](https://www.mysolution.it/fisco/informazioni/news/2023/01/10/cripto-attivita-tassazione-del-reddito-e-riporto-delle-minusvalenze), [divly](https://divly.com/it/guides/tax-loss-harvesting-crypto-italia) |
| Permute crypto-crypto | Non imponibili (fiscalmente neutre). Una fonte isolata va oltre e non è confermata. | 🟡 |
| Imposta sul valore delle cripto-attività (IVCA) | **0,2% annuo** sul valore al 31/12, per crypto non detenute presso un intermediario italiano. Presso un intermediario italiano si applica invece il **bollo 0,2%**, che versa l'intermediario. | 🟡 [centrofiscale](https://centrofiscale.com/regime-amministrato-dichiarativo-crypto-2027/) |
| Quadro RW / W (monitoraggio) | Obbligatorio per crypto su exchange esteri, wallet self-custody e DeFi. Esonero solo per le crypto detenute presso un intermediario italiano sostituto d'imposta. Sanzione dal 3% al 15% degli importi non dichiarati. | 🟡 [Bitpanda](https://www.bitpanda.com/it/italian-crypto-taxation), [centrofiscale](https://centrofiscale.com/regime-amministrato-dichiarativo-crypto-2027/) |
| Regime amministrato crypto | Previsto dalla L. 197/2022 (commi 126-147), che estende gli artt. 6-7 del D.Lgs. 461/1997. L'opzione è **scritta** e l'intermediario deve offrirlo espressamente. Costo fiscale a **costo medio ponderato** per categoria omogenea; autocertificazione del costo non ammessa. | ✅ [Interpello AdE n. 135/2025 (PDF)](https://www.dirittobancario.it/wp-content/uploads/2025/05/Agenzia-delle-Entrate-Risposta-a-interpello-14-maggio-2025-n.-135.pdf) |
| DAC8 | Dal 2026 gli exchange raccolgono i dati degli utenti; prima comunicazione all'AdE entro il 30/06/2027 | 🟡 [centrofiscale](https://centrofiscale.com/regime-amministrato-dichiarativo-crypto-2027/) |

### 2.2 Chi fa da sostituto d'imposta sulle crypto
| Intermediario | Sostituto d'imposta crypto? | Stato |
|---|---|---|
| **Cryptosmart** (Perugia, partecipata da Banca Popolare di Cortona, licenza MiCAR) | **Sì**: primo exchange italiano con regime amministrato gratuito (nessun canone). Versa imposte e bollo 0,2% via F24. Data di avvio discordante (01/01/2026 oppure 15/04/2026). **Nessuna API di trading trovata.** | ✅ (più testate: [Milano Finanza](https://www.milanofinanza.it/news/tasse-e-crypto-la-stagione-del-730-arriva-il-primo-exchange-italiano-che-paga-le-imposte-per-te-202605220957077101), [QuiFinanza](https://quifinanza.it/innovazione/cryptosmart-exchange-regime-amministrato/993630/), [AziendaBanca](https://www.aziendabanca.it/notizie/fintech-insurtech/cryptosmart-regime-fiscale-amministrato)); sito ufficiale non letto |
| **Trade Republic** | Forse (crypto vere, 1 € per ordine) | ❌ INCERTO (vedi 1.1) |
| **Conio** | Un comparatore lo indica come "Amministrato" | ❌ INCERTO: [FinanzaDigitale](https://www.finanzadigitale.com/recensioni/conio/) |
| **Young Platform** | Licenza CASP MiCAR (06/2026). Offre un report fiscale, ma non risulta sostituto d'imposta. | ❌ INCERTO (probabilmente no) |
| **Bitpanda** | **No**: lo dichiara Bitpanda stessa | ✅ [Bitpanda IT](https://www.bitpanda.com/it/italian-crypto-taxation) |
| **Scalable Capital** | Crypto solo come ETP (tassati come strumenti finanziari, redditi diversi al 26%), dentro il suo amministrato | 🟡 |
| Revolut, eToro, Binance, Coinbase, Kraken | No | 🟡 |

> **Nota utile:** un **ETP/ETN su crypto** (es. su Scalable o Trade Republic) è uno strumento finanziario e rientra nel normale regime amministrato al **26%**, non al 33%. Il trattamento esatto degli ETP crypto è 🟡: verificare con l'intermediario.

---

## 3. Regole fiscali per il motore

| # | Regola | Dettaglio operativo per il motore | Stato / fonte |
|---|---|---|---|
| 1 | **Aliquota 26%** | Plusvalenze su azioni, ETF, ETC/ETN, derivati e dividendi (D.L. 66/2014) | ✅ (norma consolidata) |
| 2 | **Titoli di Stato 12,5%** | Titoli di Stato italiani, white list e sovranazionali. In compensazione le loro plusvalenze contano per il 48,08% (12,5/26). | ✅ (D.L. 138/2011; D.M. 13/12/2011) |
| 3 | **Crypto 33%** (EMT in euro 26%) | Paniere separato (vedi §2) | ✅ / 🟡 |
| 4 | **Redditi diversi vs redditi di capitale** | **Le plusvalenze da ETF/OICR (armonizzati e non) sono redditi di capitale** (art. 44 TUIR): **non** compensano minusvalenze pregresse. **Le minusvalenze da ETF** sono redditi diversi: compensano plusvalenze su azioni, ETC, certificati e derivati. ETC/ETN/certificati: redditi diversi, plusvalenze compensabili. | ✅ più fonti concordi: [justETF](https://www.justetf.com/it/news/etf/la-fiscalita-degli-etf-in-italia.html), [MoneyViz](https://blog.moneyviz.it/tassazione-etf-2026-plusvalenze-minusvalenze-730-modello-redditi/) |
| 5 | Riforma dei redditi finanziari | **Rinviata** (PMI.it, 10/2026): l'unificazione delle categorie non è attuata. Regole invariate per il 2026. | 🟡 [PMI.it](https://www.pmi.it/finanza/risparmio/500614/riforma-fiscale-cripto-attivita.html) |
| 6 | **Scadenza minusvalenze** | Riportabili fino al **4° anno successivo** (art. 68 c.5 TUIR; art. 6 c.5 D.Lgs. 461/97 in amministrato). Il motore deve tenere un registro "zainetto" per anno di origine con scadenza al 31/12 dell'anno N+4. In amministrato lo zainetto vive presso il singolo intermediario (trasferibile solo chiudendo il rapporto). | ✅ (norma consolidata) |
| 7 | **Imposta di bollo 0,2%** | 2 per mille annuo sul valore di mercato del dossier, pro rata; nessun minimo dal 2014. Su 50 € fa circa 0,10 €/anno. In amministrato la paga l'intermediario. Sul conto corrente con giacenza media > 5.000 € si aggiungono 34,20 €. | ✅ (art. 13 c. 2-ter Tariffa DPR 642/1972) / 🟡 [money.it](https://www.money.it/Imposta-di-bollo-conto-titoli-calcolo-quanto-si-paga) |
| 8 | **Tobin tax (FTT) dal 1/1/2026** (L. 199/2025, commi 28-30) | Azioni e strumenti partecipativi di **società italiane con capitalizzazione ≥ 500 M€**: **0,2%** se acquistate su mercato regolamentato/MTF (prima 0,1%), **0,4%** OTC (prima 0,2%). Si paga sull'**acquisto**, sul saldo netto giornaliero per titolo (i round-trip intraday chiusi in giornata non la pagano). Derivati: importi fissi invariati. ETF esclusi. | ✅ [ecnews](https://www.ecnews.it/legge-di-bilancio-2026-raddoppio-delle-aliquote-di-applicazione-della-tobin-tax/); 🟡 regola del saldo netto giornaliero (norma consolidata D.M. 21/02/2013) |
| 9 | **FTT alta frequenza (HFT)** | **0,04%** (prima 0,02%) sul controvalore degli ordini su azioni o derivati italiani **annullati o modificati entro 0,5 secondi** oltre una soglia giornaliera di almeno il 60% degli ordini. Irrilevante a scala retail, ma il motore non deve fare "spam" di cancellazioni. | ✅ [ecnews](https://www.ecnews.it/legge-di-bilancio-2026-raddoppio-delle-aliquote-di-applicazione-della-tobin-tax/) |
| 10 | FTT 2027 (manovra in Parlamento) | Ipotesi: 0,2% → **0,4%** (mercati regolamentati), 0,4% → 0,6% (OTC), HFT 0,04% → 0,06%. Approvata dal CdM il 28/10/2026, **non ancora legge**. | ❌ INCERTO: [Teleborsa](https://www.teleborsa.it/News/2026/10/28/ref-231.html) |
| 11 | **Dividendi USA** | Ritenuta USA 30%, ridotta al **15% con il W-8BEN** (Convenzione Italia-USA, art. 10, L. 20/2009). In amministrato l'intermediario applica poi il 26% sul netto frontiera, per un carico totale di circa **37,1%** (senza W-8BEN circa 48,2%). Il W-8BEN vale fino al 31/12 del 3° anno successivo alla firma. | 🟡 [fiscoinvestimenti](https://fiscoinvestimenti.it/w-8ben-ritenuta-dividendi-usa/) |
| 12 | Plusvalenze su azioni USA | Nessuna ritenuta USA, solo 26% in Italia | 🟡 |
| 13 | Interessi sulla liquidità (TR, Scalable) | 26%, trattenuto dall'intermediario se in amministrato | 🟡 |
| 14 | Regole HFT/day trading per i privati | A parte la FTT HFT, in Italia non esiste una regola di tipo "PDT" USA. La regola Pattern Day Trader USA (25k $) riguarda i conti margin presso broker USA (es. Alpaca live), non i broker UE. Il trading molto frequente da privato resta "reddito diverso" (non attività d'impresa), salvo organizzazione professionale: rischio teorico, non rilevante con 50 €. | 🟡 |

**Panieri che il motore deve tenere separati:**
1. Redditi diversi al 26%: azioni, ETC/ETN, derivati, minusvalenze ETF. Lo zainetto scade al 4° anno.
2. Redditi di capitale: plusvalenze da ETF, non compensabili.
3. Crypto al 33% (EMT in euro al 26%), con zainetto separato.
4. Titoli di Stato al 12,5%, con fattore 48,08% in compensazione.
5. Costi transazionali: commissione, cambio, FTT sugli acquisti di azioni italiane ≥ 500 M€.

---

## 4. Raccomandazione

### 4.1 Impatto delle commissioni (solo commissione esplicita, **un singolo ordine**)
Ipotesi: EUR/USD circa 1,15, quindi 1 USD ≈ 0,87 € (❌ cambio indicativo). Spread esclusi. Per un **round-trip** (acquisto + vendita) il costo raddoppia circa.

| Broker / strumento | 5 € | 10 € | 25 € | Note |
|---|---|---|---|---|
| Trade Republic (1 €) | **20,0%** | **10,0%** | **4,0%** | amministrato, nessuna API |
| Scalable FREE (0,99 €) | 19,8% | 9,9% | 4,0% | amministrato dal 09/2026, nessuna API |
| Saxo, azioni USA (1 $ + 0,25% di cambio) | 17,6% | 8,9% | 3,7% | amministrato, OpenAPI; nessuna frazione, quindi un ordine da 5 € compra solo titoli sotto i 5 € |
| Saxo, azioni IT (2 € + FTT 0,2%) | 40,2% | 20,2% | 8,2% | |
| Directa, azioni IT (min 1,5 € + FTT 0,2%) | 30,2% | 15,2% | 6,2% | amministrato, API; più 20 €/mese di datafeed ❌ |
| Fineco (min 2,95 €) | 59,0% | 29,5% | 11,8% | |
| DEGIRO (circa 2 €) | 40,0% | 20,0% | 8,0% | dichiarativo |
| IBKR, USA Fixed (max 1%) | 1,0% | 1,0% | 1,0% | dichiarativo; più circa 2 $ minimi per conversione valuta |
| Trading 212 / Alpaca | ~0,15% / 0% | ~0,15% / 0% | ~0,15% / 0% | dichiarativo |

**Conclusione numerica:** con il regime amministrato, sotto i 25 € per ordine ogni trade costa almeno il 4% (8% andata e ritorno). Per stare sotto l'1% per lato servono **ordini da almeno 100 €** con TR/Scalable/Saxo USA. Con 50 € di capitale, una strategia ad alta rotazione in amministrato perde quasi certamente per le sole commissioni. Il motore deve:
- imporre una **dimensione minima per ordine** (es. costo per lato ≤ 1–2%);
- usare **pochi trade**, con orizzonte settimanale o mensile;
- preferire i **piani d'accumulo gratuiti** di TR/Scalable (0 €, da 1 €) per gli ingressi periodici in ETF.

### 4.2 (a) Paper trading con API gratuita
| Opzione | Pro | Contro |
|---|---|---|
| **Alpaca Paper (prima scelta per sviluppare il motore)** | Gratis, solo email, aperto a chiunque nel mondo, REST + WebSocket, SDK ufficiali, azioni USA + crypto, frazioni | Solo mercato USA, dati IEX, non simula fee e dividendi. Il motore deve aggiungere un **modello costi "italiano"** (1 € o 0,99 € fissi, FTT, 26/33%). |
| **Saxo SIM (seconda, in parallelo)** | Gratis, multi-mercato (IT/UE/USA), **stessa API del live in amministrato**, quindi il codice si riusa | Token di 24 h (in seguito serve OAuth), curva di apprendimento più ripida |
| Trading 212 demo API | Gratis, azioni UE/USA, frazioni | API beta, ordini non idempotenti; il live è dichiarativo, quindi serve solo come simulatore |
| IBKR paper | API completa | Richiede l'apertura di un conto IBKR reale |

### 4.3 (b) Live in regime amministrato
| Opzione | Automazione | Costo con 50 € | Verdetto |
|---|---|---|---|
| **A. Ibrido "segnali automatici + 1 tap" su Trade Republic** (oppure Scalable FREE) | Il motore genera il segnale e lo notifica (es. Telegram o email, gratis). L'utente esegue a mano nell'app. | 1 € (0,99 €) per ordine, frazioni da 1 € | ✅ **Consigliata per partire**: amministrato verificato, frazioni, zero canoni, nessun rischio ToS. Limite: niente ordini limite sulle frazioni, esecuzione manuale e quindi ritardi. |
| **B. Saxo Italia + OpenAPI** | Completa (REST) | 1 $ per ordine USA, 2 € per ordine IT, nessuna frazione | 🟡 **Unica automazione "pulita" in amministrato** se Saxo conferma l'accesso OpenAPI live ai clienti italiani e i costi dei dati in tempo reale. Con 50 € e senza frazioni l'universo investibile è minimo. Da rivalutare con un capitale ≥ 500–1.000 €. |
| **C. Directa + dAPI** | Completa, ma Darwin deve essere acceso (PC sempre attivo), login con OTP, disconnessione notturna | Min 1,5 € (IT), circa 9 $ (USA), più datafeed 20 €/mese ❌ | ❌ Sfora il budget di 0 € (se il datafeed è davvero obbligatorio) e non ha frazioni né conto di prova |
| D. TR/DEGIRO con API non ufficiali | Completa | — | ⛔ **Sconsigliata** (ToS, blocco del conto, sicurezza) |
| E. IBKR / Alpaca / T212 live | Completa e ottima | Costi minimi | ⛔ Dichiarativo: viola il vincolo "zero adempimenti" (RT, RW, IVAFE ogni anno) |

**Crypto live in amministrato:** **Cryptosmart** (sostituto d'imposta verificato da più testate, nessuna API trovata, quindi solo modalità ibrida) oppure **ETP crypto** su TR/Scalable (26%, dentro l'amministrato già esistente). Le crypto "vere" su TR sono ❌ da verificare.

### 4.4 Combinazione consigliata
1. **Fase paper:** Alpaca Paper (API) per costruire il motore, con un modello costi che simuli TR (1 €/ordine) e la fiscalità italiana. In parallelo, un'app su Saxo SIM per validare l'integrazione futura.
2. **Fase live (50 €):** **Trade Republic in modalità ibrida** (segnali automatici, esecuzione manuale con un tap). Ordini rari, ≥ 25 € (meglio ≥ 50 €), oppure piani d'accumulo gratuiti.
3. **Quando il capitale cresce (≥ 1.000 €):** valutare **Saxo Italia + OpenAPI** per l'automazione completa in amministrato, dopo conferma scritta da Saxo su (i) accesso OpenAPI live per clienti di Saxo SIM e (ii) costi dei dati in tempo reale.

### 4.5 Cose da verificare direttamente (lista di controllo)
- [ ] Trade Republic: le crypto rientrano nel regime amministrato? Esiste un importo minimo per ordine in frazioni? (supporto TR)
- [ ] Saxo Italia: OpenAPI live disponibile per i clienti di Saxo SIM? Frazioni? Costo dei dati in tempo reale? Deposito minimo?
- [ ] Directa: il DATAFEED da 20 €/mese è obbligatorio per usare il socket di trading? Esistono esenzioni?
- [ ] Scalable: ordini singoli in frazioni? Crypto/ETP dentro l'amministrato?
- [ ] Cryptosmart: commissioni di trading, data effettiva di avvio, eventuali API.
- [ ] Testo della manovra 2027 (FTT) una volta approvata (entro fine dicembre 2026).
