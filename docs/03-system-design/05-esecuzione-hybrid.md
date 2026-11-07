# 3.5 — Esecuzione: paper, hybrid, live

## Adapter (trait Rust `ExecutionAdapter`)
```rust
trait ExecutionAdapter {
    fn submit(&self, order: CheckedOrder) -> Result<SubmissionId>;   // CheckedOrder si crea SOLO da guardrails::check_order
    fn status(&self, id: &SubmissionId) -> Result<OrderStatus>;
    fn cancel(&self, id: &SubmissionId) -> Result<()>;
}
```
`CheckedOrder` ha un costruttore privato: l'unico modo per ottenerne uno è passare dai guardrails. È il **compilatore** a garantire che nessun ordine li salti.

| Adapter | Modalità | Fill |
|---|---|---|
| `SimBroker` | paper / backtest | prezzo di apertura del giorno successivo ± spread/2, più la commissione del profilo Trade Republic |
| `AlpacaPaper` | paper | fill reale simulato da Alpaca; il costo viene comunque ricalcolato con il profilo Trade Republic |
| `ManualTap` | hybrid | l'utente esegue su Trade Republic e conferma |
| `Saxo` / `Ibkr` | live (futuro) | API |

## Vincoli reali di Trade Republic (verificati, [approfondimenti](../01-raccolta/approfondimenti-fase3.md))
- **Frazioni solo con ordini a mercato.** Ordini limite e stop sono possibili solo su quote intere. Con 50 € quasi tutti gli ordini sono frazionari.
- **Il "prezzo limite" di G-09 diventa un *prezzo massimo accettabile*:** la notifica lo mostra, l'utente confronta col prezzo nell'app prima del tap e, se è sopra, non esegue e preme "⏭ Salta". Su quote intere resta un vero ordine limite.
- **Esecuzione predefinita "Best Price" (1 €)** dal 2 luglio 2026: Trade Republic fa da controparte. Scegliere una borsa specifica ("Direct Price") costa 2 €, quindi non si usa.
- **Piano di accumulo:** gratuito, da 10 € per esecuzione.
- **Export CSV** disponibile nell'app dal 15/04/2026 (problemi noti: dividendi duplicati, alcune commissioni). La riconciliazione deve deduplicare.

## Ciclo di vita di una proposta (hybrid)
```
        guardrails OK
Draft ───────────────▶ Pending ──notifica──▶ Notified ──"✅ Eseguito" + prezzo/qty──▶ Filled
  │                                            │  │  │
  └─ violazioni ─▶ Rejected (ledger)           │  │  └──"⏭ Salta"──▶ Skipped
                                               │  └──── scaduta TTL ──▶ Expired
                                               └─ nuovo segnale / stato di rischio cambiato / prezzo oltre il limite ──▶ Invalidated
```
- **Ricontrollo al tap:** prima di registrare il fill il motore rilancia `check_order` con lo stato aggiornato. Se nel frattempo è scattato il soft stop, la conferma viene accettata ma marcata "eseguita fuori regola" e segnalata.
- **Prezzo eseguito oltre il limite** (l'utente ha eseguito comunque): il fill viene registrato con un avviso, e la differenza alimenta la calibrazione degli spread.
- **Idempotenza:** ogni proposta ha un `proposal_id`. Una doppia conferma non genera due fill.

## Contenuto della notifica (Telegram + Web Push)
```
🟢 COMPRA  iShares Core MSCI World (IE00B4L5Y983)
Importo: 52,00 €   ·  Prezzo max accettabile: 108,40 € (ordine a mercato frazionario)  ·  Valida fino a: ven 14/11 18:00
Perché: trend positivo su 1/3/6/12 mesi; sostituisce Emergenti (uscito dalla top 5)
Costi: 1,00 € (1,9%)  ·  Rendimento atteso a 1 mese: +4,1% (stima prudente)
Dopo l'acquisto imposta lo STOP a: — (ETF core, nessuno stop)
[✅ Eseguito]  [⏭ Salta]  [ℹ️ Dettagli]
```
- Su "✅ Eseguito" il bot chiede il prezzo effettivo e la quantità (precompilati con i valori proposti: basta confermare).
- **Stop-loss:** su Trade Republic si può piazzare solo su quote intere. Le posizioni frazionarie hanno quindi uno **stop monitorato dal sistema**: al superamento arriva una notifica urgente "VENDI", ripetuta ogni ora finché non arriva la conferma. ⚠️ Non è automatico: se l'utente non risponde, la posizione resta aperta. Per questo S1 si attiva solo oltre ~500 € (vedi 3.2), quando è più probabile comprare quote intere con lo stop sul broker.
- I promemoria arrivano a metà e a fine della finestra di validità.

## Riconciliazione
- **Settimanale:** l'utente carica nella webapp l'estratto o export di Trade Republic (CSV dall'app). Il sistema confronta posizioni e cassa col ledger e crea un evento `Reconciliation`. Le differenze vengono segnalate e risolte con eventi correttivi, mai con modifiche.
- **Piano di accumulo:** gli acquisti automatici del core vengono registrati dalla riconciliazione, oppure con un tap rapido ("PAC eseguito") alla data prevista.

## Paper trading (Gate 1)
- Tutto in automatico: `SimBroker` per tutti gli strumenti; in parallelo `AlpacaPaper` sulle azioni USA, per misurare la differenza tra fill simulato e fill "quasi reale".
- Capitale simulato: due conti paper in parallelo, uno da **50 €** (realtà) e uno da **1.000 €** (per validare i satellite che con 50 € non si attivano).

## Implementazione del paper trading (M6, 2026-11-07)
| Passo | Chi | Cosa |
|---|---|---|
| 1. ingest | Python | prezzi, cambi e tassi del giorno |
| 2. feed | Python (`paper/feed.py`) | prezzo "UCITS sintetico" in EUR, **append-only**: si salva solo il rendimento del giorno, così le serie rettificate riscritte dopo un dividendo non alterano le valutazioni già fatte |
| 3. `money-engine settle` | Rust | SimBroker: esegue gli ordini all'apertura del giorno previsto con i costi di Trade Republic; poi versamenti, interessi (€STR, 26%) e bollo |
| 4. decide | Python (`paper/runner.py`) | stesse strategie del backtest; lo stato (es. stima dell'edge) è scaldato sulla storia senza simulare P&L e salvato ogni giorno |
| 5. `money-engine execute` | Rust | ogni intenzione passa da `guardrails::check` → `CheckedOrder` (costruttore privato) → ordine SimBroker + copia ombra su **Alpaca Paper** (solo confronto dei fill); valutazione e macchina del rischio |

- **G-17:** il motore rifiuta di partire se `mode` non è `paper`, e il client Alpaca accetta solo l'endpoint `paper-api`.
- **Idempotenza:** una decisione al giorno per conto. Se ci sono ordini in attesa la decisione si rimanda. Gli eventi di cassa si registrano solo a ordini chiusi, così le date del ledger restano in ordine.
- **Conti:** `config/paper.toml` (50 €, 1.000 €, 10.000 € di diagnostica). Schedulazione su Mac con `infra/paper/com.money.paper.plist`; sulla VM con cron (M9).
- **Soft stop:** nel paper la ripartenza non è automatica (come nel live). Il comando di ripartenza manuale arriverà con la webapp (M7).
