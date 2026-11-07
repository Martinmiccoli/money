import { useCallback, useEffect, useState } from "react";
import {
  type Account,
  dateIt,
  dateTimeIt,
  type EquityPoint,
  eur,
  get,
  type Guardrails,
  type Health,
  type LedgerItem,
  type Order,
  pct,
  type Position,
  resume,
} from "./api";
import { LineChart } from "./LineChart";

const STRATEGY: Record<string, string> = {
  savings_plan: "Piano di accumulo",
  s3s4_s8: "Trend + rotazione + regime",
  s3_monthly_equal: "Trend (diagnostica)",
  s3_monthly_vol: "Trend con vol scaling",
  s4_top3: "Rotazione settoriale",
};

const RISK: Record<string, { label: string; tone: string }> = {
  Active: { label: "Attivo", tone: "ok" },
  Suspended: { label: "Sospeso (G-01)", tone: "warn" },
  Locked: { label: "Bloccato (G-02)", tone: "bad" },
};

export function App() {
  const [accounts, setAccounts] = useState<Account[] | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [guard, setGuard] = useState<Guardrails | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    Promise.all([get<Account[]>("/api/accounts"), get<Health>("/api/health"), get<Guardrails>("/api/guardrails")])
      .then(([a, h, g]) => {
        setAccounts(a);
        setHealth(h);
        setGuard(g);
        setSelected((s) => s ?? a[0]?.account ?? null);
      })
      .catch((e) => setError(String(e)));
  }, []);
  useEffect(load, [load]);

  const current = accounts?.find((a) => a.account === selected);
  return (
    <main>
      <header>
        <h1>Money</h1>
        <span className="pill">
          modalità <b>{guard?.config.mode ?? "…"}</b> · soldi finti
        </span>
      </header>
      {error && <p className="banner bad">Errore: {error}</p>}
      {health && <HealthBanner health={health} />}

      <section className="cards">
        {accounts?.map((a) => (
          <button
            key={a.account}
            className={`card ${a.account === selected ? "selected" : ""}`}
            onClick={() => setSelected(a.account)}
          >
            <div className="card-head">
              <span>{a.account}</span>
              <span className={`dot ${RISK[a.risk_state]?.tone ?? "ok"}`} title={RISK[a.risk_state]?.label} />
            </div>
            <div className="big">{eur(a.nav)}</div>
            <div className={(a.return_pct ?? 0) >= 0 ? "pos" : "neg"}>{pct(a.return_pct)} sul versato</div>
            <div className="muted">{STRATEGY[a.strategy] ?? a.strategy}</div>
          </button>
        ))}
      </section>

      {current && <AccountDetail key={current.account} account={current} codes={guard?.codes ?? {}} onChange={load} />}
      {guard && <GuardrailsPanel guard={guard} />}
      <footer className="muted">
        Risultati simulati: non sono una previsione. I numeri fiscali vanno verificati da un commercialista.
      </footer>
    </main>
  );
}

function HealthBanner({ health }: { health: Health }) {
  const failed = health.heartbeats.filter((h) => h.status !== "ok" && h.status !== "running");
  const last = health.heartbeats.map((h) => h.at).sort().at(-1);
  if (failed.length)
    return (
      <p className="banner bad">
        ⚠️ Problemi: {failed.map((f) => `${f.component} (${dateTimeIt(f.at)})`).join(", ")}
      </p>
    );
  return (
    <p className="banner ok">
      Ultimo giro: {dateTimeIt(last)} · prezzi disponibili fino a {dateTimeIt(health.prices_available_at)}
    </p>
  );
}

function AccountDetail({
  account,
  codes,
  onChange,
}: {
  account: Account;
  codes: Record<string, string>;
  onChange: () => void;
}) {
  const [equity, setEquity] = useState<EquityPoint[]>([]);
  const [positions, setPositions] = useState<Position[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [events, setEvents] = useState<LedgerItem[]>([]);
  const [msg, setMsg] = useState<string | null>(null);
  const id = account.account;

  useEffect(() => {
    get<EquityPoint[]>(`/api/accounts/${id}/equity`).then(setEquity);
    get<Position[]>(`/api/accounts/${id}/positions`).then(setPositions);
    get<Order[]>(`/api/accounts/${id}/orders`).then(setOrders);
    get<LedgerItem[]>(`/api/accounts/${id}/events?limit=60`).then(setEvents);
  }, [id]);

  const invested = positions.reduce((s, p) => s + (p.value ?? 0), 0);
  const doResume = async () => {
    if (!confirm("Ripartire? Il nuovo massimo di riferimento diventa il valore attuale.")) return;
    const r = await resume(id);
    setMsg(r.message);
    onChange();
  };

  return (
    <section className="detail">
      <div className="detail-head">
        <h2>{id}</h2>
        <span className={`pill ${RISK[account.risk_state]?.tone}`}>{RISK[account.risk_state]?.label}</span>
        {account.risk_state === "Suspended" && (
          <button className="action" onClick={doResume}>
            Riparti dopo il soft stop
          </button>
        )}
      </div>
      {msg && <p className="banner">{msg}</p>}
      {account.notes && <p className="muted">{account.notes}</p>}

      <div className="stats">
        <Stat label="Valore" value={eur(account.nav)} />
        <Stat label="Versato" value={eur(account.net_deposits)} />
        <Stat label="Rendimento" value={pct(account.return_pct)} />
        <Stat label="Max drawdown" value={pct(account.max_drawdown)} />
        <Stat label="Giorni" value={String(account.days)} />
        <Stat label="Ordini eseguiti" value={String(account.fills)} />
      </div>

      <h3>Andamento</h3>
      <LineChart points={equity.map((e) => ({ x: e.date, y: e.nav, y2: e.deposits }))} />

      <h3>Posizioni</h3>
      {positions.length === 0 ? (
        <p className="muted">Nessuna posizione: tutto in liquidità.</p>
      ) : (
        <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Strumento</th>
              <th className="num">Quote</th>
              <th className="num">Prezzo</th>
              <th className="num">Valore</th>
              <th className="num">Peso</th>
            </tr>
          </thead>
          <tbody>
            {positions.map((p) => (
              <tr key={p.instrument}>
                <td>
                  {p.name}
                  <div className="muted small">{p.instrument}</div>
                </td>
                <td className="num">{p.qty.toLocaleString("it-IT", { maximumFractionDigits: 4 })}</td>
                <td className="num">{eur(p.close)}</td>
                <td className="num">{eur(p.value)}</td>
                <td className="num">{account.nav ? pct((p.value ?? 0) / account.nav, 1) : "—"}</td>
              </tr>
            ))}
            <tr>
              <td>Liquidità</td>
              <td />
              <td />
              <td className="num">{eur(account.nav == null ? null : account.nav - invested)}</td>
              <td />
            </tr>
          </tbody>
        </table>
</div>
      )}

      {account.rejections.length > 0 && (
        <>
          <h3>Ordini bloccati dai guardrails</h3>
          <ul className="codes">
            {account.rejections.map((r) => (
              <li key={r.code}>
                <b>{r.code}</b> × {r.n} — {codes[r.code] ?? ""}
              </li>
            ))}
          </ul>
        </>
      )}

      <h3>Ordini</h3>
      {orders.length === 0 ? (
        <p className="muted">Nessun ordine.</p>
      ) : (
        <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Esecuzione</th>
              <th>Ordine</th>
              <th>Stato</th>
              <th className="num">Prezzo simulato</th>
              <th>Alpaca (ombra)</th>
            </tr>
          </thead>
          <tbody>
            {orders.map((o) => (
              <tr key={o.order_id}>
                <td>{dateIt(o.exec_date)}</td>
                <td>
                  {o.side === "buy" ? "Compra" : "Vendi"} {o.side === "buy" ? eur(o.notional) : `${o.qty} quote`} di{" "}
                  {o.instrument_id}
                </td>
                <td>{o.status === "pending" ? "in attesa" : o.status === "filled" ? "eseguito" : o.status}</td>
                <td className="num">{o.fill?.price_eur ? eur(Number(o.fill.price_eur)) : "—"}</td>
                <td>
                  {o.symbol ?? "—"} {o.alpaca_status ?? ""}{" "}
                  {o.alpaca_price ? `@ ${o.alpaca_price.toLocaleString("it-IT")} $` : ""}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
</div>
      )}

      <h3>Registro (ledger)</h3>
      <ol className="timeline">
        {events.map((e) => (
          <li key={e.seq} className={`ev ${e.kind}`}>
            <span className="muted small">
              #{e.seq} · {dateIt(e.date)}
            </span>
            <span>{e.text}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="stat">
      <div className="muted small">{label}</div>
      <div className="stat-v">{value}</div>
    </div>
  );
}

function GuardrailsPanel({ guard }: { guard: Guardrails }) {
  const c = guard.config;
  const rows: [string, string][] = [
    ["G-01 soft stop", `−${c.drawdown?.soft_stop_pct}% dal massimo`],
    ["G-02 kill switch", `−${c.drawdown?.hard_kill_pct}% del versato`],
    ["G-05 costo massimo", `${c.orders?.max_cost_ratio_pct}% del controvalore`],
    ["G-06 edge minimo", `${c.orders?.min_edge_to_cost}× il costo andata e ritorno`],
    ["G-07 ordini", `${c.orders?.max_orders_per_day}/giorno, ${c.orders?.max_orders_per_week}/settimana`],
    ["G-08 crypto", `max ${c.positions?.max_crypto_etp_total_pct}% del conto`],
    ["G-10 dati", `max ${c.data?.max_staleness_hours} ore`],
  ];
  return (
    <details className="guard">
      <summary>Guardrails attivi</summary>
      <div className="table-wrap">
      <table>
        <tbody>
          {rows.map(([k, v]) => (
            <tr key={k}>
              <td>{k}</td>
              <td>{v}</td>
            </tr>
          ))}
        </tbody>
      </table>
</div>
    </details>
  );
}
