export type Account = {
  account: string;
  strategy: string;
  started_on: string;
  notes: string | null;
  nav: number | null;
  date: string | null;
  net_deposits: number;
  risk_state: string;
  return_pct: number | null;
  max_drawdown: number;
  days: number;
  fills: number;
  rejections: { code: string; n: number }[];
};
export type EquityPoint = { date: string; nav: number; deposits: number; risk_state: string };
export type Position = { instrument: string; name: string; qty: number; close: number | null; value: number | null };
export type LedgerItem = { seq: number; date: string; kind: string; text: string; hash: string };
export type Order = {
  order_id: string;
  instrument_id: string;
  side: string;
  notional: number | null;
  qty: number | null;
  exec_date: string;
  status: string;
  fill: { price_eur?: string; qty?: string } | null;
  symbol: string | null;
  alpaca_status: string | null;
  alpaca_price: number | null;
};
export type Health = {
  heartbeats: { component: string; at: string; status: string; detail: string | null }[];
  prices_available_at: string | null;
};
export type Guardrails = { config: Record<string, any>; codes: Record<string, string> };

export async function get<T>(path: string): Promise<T> {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`${path}: ${r.status}`);
  return r.json() as Promise<T>;
}

export async function resume(account: string): Promise<{ ok: boolean; message: string }> {
  const r = await fetch(`/api/accounts/${account}/resume`, { method: "POST", headers: { "x-money-action": "resume" } });
  return r.json();
}

export const eur = (v: number | null | undefined) =>
  v == null ? "—" : v.toLocaleString("it-IT", { style: "currency", currency: "EUR" });
export const pct = (v: number | null | undefined, d = 2) =>
  v == null ? "—" : `${v >= 0 ? "+" : ""}${(v * 100).toLocaleString("it-IT", { maximumFractionDigits: d, minimumFractionDigits: d })}%`;
export const dateIt = (d: string | null | undefined) => (d ? new Date(d).toLocaleDateString("it-IT") : "—");
export const dateTimeIt = (d: string | null | undefined) =>
  d ? new Date(d).toLocaleString("it-IT", { dateStyle: "short", timeStyle: "short" }) : "—";
