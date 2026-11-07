// Funzioni pure: testo leggibile degli eventi del ledger e posizioni. Testate in test/format.test.ts.

export type LedgerEvent = { kind: string; [k: string]: unknown };

const eur = (v: unknown) =>
  `${Number(v ?? 0).toLocaleString("it-IT", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €`;
const num = (v: unknown, d = 6) => Number(v ?? 0).toLocaleString("it-IT", { maximumFractionDigits: d });
const verb = (side: unknown) => (side === "buy" ? "compra" : "vendi");

/** Descrizione in italiano di un evento del ledger (per la timeline della webapp e per Telegram). */
export function describe(e: LedgerEvent): string {
  switch (e.kind) {
    case "Deposit":
      return `Versamento di ${eur(e.amount_eur)}`;
    case "Withdrawal":
      return `Prelievo di ${eur(e.amount_eur)}`;
    case "Fill":
      return `${e.side === "buy" ? "Comprate" : "Vendute"} ${num(e.qty)} quote di ${e.instrument} a ${eur(
        e.price_eur,
      )} (commissione ${eur(e.commission_eur)})`;
    case "TaxWithheld":
      return `Imposta trattenuta: ${eur(e.amount_eur)}${e.reference ? ` (${e.reference})` : ""}`;
    case "StampDuty":
      return `Imposta di bollo: ${eur(e.amount_eur)}`;
    case "Interest":
      return `Interessi sulla liquidità: ${eur(e.amount_eur)} lordi`;
    case "Dividend":
      return `Dividendo ${e.instrument}: ${eur(e.gross_eur)} lordi`;
    case "OrderSubmitted":
      return e.side === "buy"
        ? `Ordine inviato: ${verb(e.side)} ${eur(e.notional_eur)} di ${e.instrument} — ${e.reason}`
        : `Ordine inviato: ${verb(e.side)} ${num(e.qty)} quote di ${e.instrument} — ${e.reason}`;
    case "OrderRejected":
      return `Ordine bloccato [${(e.codes as string[]).join(", ")}]: ${verb(e.side)} ${e.instrument}`;
    case "OrderExpired":
      return `Ordine scaduto (${e.order_id}): ${e.reason}`;
    case "RiskStateChanged":
      return `Rischio: ${e.from} → ${e.to} (valore ${eur(e.equity_eur)})`;
    case "ConfigChanged":
      return `Configurazione cambiata (${String(e.config_sha256).slice(0, 8)})`;
    case "Reconciliation":
      return `Riconciliazione ${e.ok ? "ok" : "con differenze"}: ${e.detail}`;
    default:
      return e.kind;
  }
}

/** Spiegazione breve dei codici dei guardrails più frequenti. */
export const GUARDRAIL_TEXT: Record<string, string> = {
  "G-01": "soft stop: niente nuovi acquisti dopo un calo del 15% dal massimo",
  "G-02": "kill switch: conto bloccato",
  "G-03": "vendita oltre la posizione",
  "G-04": "liquidità insufficiente",
  "G-05": "costo dell'ordine oltre il 2% del controvalore",
  "G-06": "rendimento atteso troppo basso rispetto ai costi",
  "G-07": "troppi ordini nel giorno o nella settimana",
  "G-08": "posizione troppo grande",
  "G-10": "dati di mercato troppo vecchi",
  "G-13": "strumento non ammesso",
};

export type Fill = { instrument: string; side: string; qty: string };

/** Quantità posseduta per strumento a partire dai fill (solo visualizzazione: la contabilità è nel ledger). */
export function positionsFromFills(fills: Fill[]): Map<string, number> {
  const m = new Map<string, number>();
  for (const f of fills) {
    const q = Number(f.qty) * (f.side === "buy" ? 1 : -1);
    m.set(f.instrument, (m.get(f.instrument) ?? 0) + q);
  }
  for (const [k, v] of m) if (Math.abs(v) < 1e-9) m.delete(k);
  return m;
}

/** Massimo drawdown di una serie di valori (negativo, es. -0.12). */
export function maxDrawdown(values: number[]): number {
  let peak = -Infinity;
  let mdd = 0;
  for (const v of values) {
    peak = Math.max(peak, v);
    if (peak > 0) mdd = Math.min(mdd, v / peak - 1);
  }
  return mdd;
}
