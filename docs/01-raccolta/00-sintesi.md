# Fase 1 — Sintesi della raccolta (2026-11-06)

Rapporti di dettaglio:
- [broker-e-fisco.md](broker-e-fisco.md)
- [fonti-dati-e-hosting.md](fonti-dati-e-hosting.md)
- [top-player-e-soluzioni.md](top-player-e-soluzioni.md)
- [letteratura.md](letteratura.md)

## 1. Verità che vincolano il progetto
1. **Con 50 € decidono i costi.** Con 1 € di commissione per lato si paga il 20% su un ordine da 5 €, il 10% su 10 € e il 4% su 25 €. Per restare sotto l'1% servono ordini da almeno 100 €. Il motore quindi deve fare **pochi trade, con frequenza da settimanale a mensile**. "Micro" va inteso come importo piccolo, non come alta frequenza.
2. **Il benchmark da battere è un ETF al netto dei costi.** La maggior parte dei retail attivi perde contro il mercato, e lo Sharpe di un backtest non predice quasi nulla del risultato live (R² < 0,025 su 888 algoritmi).
3. **Le anomalie pubblicate si indeboliscono.** I segnali di ML sono piccoli (R² fuori campione < 1%). Gli LLM servono come estrattori di feature, non come trader autonomi.
4. **Il regime amministrato con API ufficiale è quasi inesistente.** Trade Republic e Scalable fanno da sostituto d'imposta ma non hanno API. Le opzioni con API sono Directa (costosa, senza frazioni) e Saxo (accesso API per i clienti italiani da confermare).

## 2. Pilastri dei segnali alla luce delle evidenze
| Pilastro | Evidenza | Uso nel sistema |
|---|---|---|
| Insider buying (Form 4, cluster, "opportunistic") | Forte (Cohen-Malloy-Pomorski: +82 bp/mese) | **Segnale primario** sulle azioni USA |
| Superinvestor 13F (consenso value) | Rende circa come il mercato, dati in ritardo di 45 giorni | Universo e base di qualità |
| Fattori (momentum, trend, quality, low-vol) | Solida ma in decadimento | **Motore principale** su ETF |
| Sentiment (news, GDELT, Google Trends) | Contrarian e di breve periodo, in erosione | Filtro anti-hype e gestione del rischio |
| Congresso USA | Nessun vantaggio in media, tranne i leader | Segnale secondario |
| ML / LLM | Gradient boosting > deep learning; LLM come feature extractor | Combinazione dei segnali e scoring del testo |

## 3. Architettura emersa (da confermare nella Fase 2)
- **Paper trading:** Alpaca Paper (gratuito), con un modello dei **costi e del fisco italiano** simulato.
- **Live con 50 €:** **modalità ibrida**. Il sistema calcola gli ordini e l'utente li esegue con un tap su **Trade Republic** (regime amministrato, frazioni da 1 €, circa 1 € a ordine).
- **Automazione totale:** solo oltre circa 1.000 € di capitale, tramite Saxo OpenAPI (da confermare).
- **Crypto:** gli **ETP crypto** rientrano nel regime amministrato con aliquota al 26%. Le crypto dirette sono al 33% e quasi nessun intermediario fa da sostituto d'imposta, quindi restano solo nel paper trading.
- **Azioni italiane:** priorità bassa, perché non c'è una fonte dati gratuita affidabile e si paga la Tobin tax dello 0,2%.
- **Hosting:** Oracle Cloud Always Free (2 OCPU e 12 GB) per motore Rust, job Python, API TypeScript e Postgres. Cloudflare davanti, GitHub Actions come watchdog e backup.
- **Dati:** Alpaca data, SEC EDGAR (13F e Form 4), dump Binance, GDELT, Marketaux, FRED, ECB.
- **Framework:** NautilusTrader (core in Rust) è il candidato, **ma non supporta Alpaca**. Le alternative sono un engine Rust leggero scritto da noi con un adapter per Alpaca, oppure Nautilus solo per il backtest.

## 4. Decisioni richieste all'utente
1. La modalità ibrida (tap manuale) per il live con 50 € è accettabile?
2. Crypto tramite ETP nel live e crypto dirette solo in paper: ok?
3. Frequenza di trading da settimanale a mensile: ok?
4. Azioni italiane fuori dal live iniziale: ok?
