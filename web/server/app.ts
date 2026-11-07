// API in sola lettura sul DB, più l'azione di ripartenza dopo un soft stop (G-01).
import { spawn } from "node:child_process";
import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import { Hono } from "hono";
import type { Sql } from "postgres";
import { parse } from "smol-toml";
import { describe, GUARDRAIL_TEXT, maxDrawdown, positionsFromFills, type LedgerEvent } from "./format.js";

export const REPO = resolve(import.meta.dirname, "../..");
const ENGINE = resolve(REPO, "engine/target/release/money-engine");

type Resume = (account: string) => Promise<{ ok: boolean; message: string }>;

export function runEngineResume(account: string): Promise<{ ok: boolean; message: string }> {
  return new Promise((done) => {
    if (!existsSync(ENGINE)) return done({ ok: false, message: "money-engine non compilato" });
    const p = spawn(ENGINE, ["resume", "--account", account], { cwd: REPO, env: { ...process.env, MONEY_REPO: REPO } });
    let out = "";
    p.stdout.on("data", (d) => (out += d));
    p.stderr.on("data", (d) => (out += d));
    p.on("close", (code) => done({ ok: code === 0, message: out.trim() }));
  });
}

export function createApp(sql: Sql, resume: Resume = runEngineResume) {
  const app = new Hono();

  app.get("/api/health", async (c) => {
    const beats = await sql`
      SELECT DISTINCT ON (component) component, at, status, detail
      FROM ops.heartbeat ORDER BY component, at DESC`;
    const fresh = await sql`SELECT max(available_at) AS at FROM paper.price_eur`;
    return c.json({ heartbeats: beats, prices_available_at: fresh[0]?.at ?? null });
  });

  app.get("/api/guardrails", (c) => {
    const cfg = parse(readFileSync(resolve(REPO, "config/guardrails.toml"), "utf8"));
    return c.json({ config: cfg, codes: GUARDRAIL_TEXT });
  });

  app.get("/api/accounts", async (c) => {
    const accounts = await sql`SELECT account, strategy, started_on, initial_deposit_eur, notes FROM paper.account
                               WHERE active ORDER BY initial_deposit_eur`;
    const out = [];
    for (const a of accounts) {
      const eq = await sql`SELECT date, nav_eur, net_deposits_eur, risk_state, high_water_mark_eur
                           FROM paper.equity_daily WHERE account=${a.account} ORDER BY date`;
      const kinds = await sql`SELECT kind, count(*)::int n FROM ledger.event WHERE account=${a.account} GROUP BY kind`;
      const codes = await sql`
        SELECT c AS code, count(*)::int n FROM ledger.event, jsonb_array_elements_text(record->'event'->'codes') c
        WHERE account=${a.account} AND kind='OrderRejected' GROUP BY c ORDER BY n DESC`;
      const last = eq.at(-1);
      const navs = eq.map((r) => Number(r.nav_eur));
      out.push({
        ...a,
        nav: last ? Number(last.nav_eur) : null,
        date: last?.date ?? null,
        net_deposits: last ? Number(last.net_deposits_eur) : Number(a.initial_deposit_eur),
        risk_state: last?.risk_state ?? "Active",
        return_pct: last ? Number(last.nav_eur) / Number(last.net_deposits_eur) - 1 : null,
        max_drawdown: maxDrawdown(navs),
        days: eq.length,
        fills: kinds.find((k) => k.kind === "Fill")?.n ?? 0,
        rejections: codes,
      });
    }
    return c.json(out);
  });

  app.get("/api/accounts/:id/equity", async (c) => {
    const rows = await sql`SELECT date, nav_eur::float nav, net_deposits_eur::float deposits, risk_state
                           FROM paper.equity_daily WHERE account=${c.req.param("id")} ORDER BY date`;
    return c.json(rows);
  });

  app.get("/api/accounts/:id/positions", async (c) => {
    const id = c.req.param("id");
    const fills = await sql`SELECT record->'event'->>'instrument' instrument, record->'event'->>'side' side,
                                   record->'event'->>'qty' qty
                            FROM ledger.event WHERE account=${id} AND kind='Fill' ORDER BY seq`;
    const pos = positionsFromFills(fills as unknown as { instrument: string; side: string; qty: string }[]);
    const out = [];
    for (const [instrument, qty] of pos) {
      const px = await sql`SELECT p.close_eur::float close, p.date, i.name FROM paper.price_eur p
                           JOIN ref.instrument i USING (instrument_id)
                           WHERE instrument_id=${instrument} ORDER BY date DESC LIMIT 1`;
      const close = px[0]?.close ?? null;
      out.push({ instrument, name: px[0]?.name ?? instrument, qty, close, value: close == null ? null : qty * close, date: px[0]?.date });
    }
    return c.json(out);
  });

  app.get("/api/accounts/:id/events", async (c) => {
    const limit = Math.min(Number(c.req.query("limit") ?? 100), 500);
    const rows = await sql`SELECT seq, date, kind, record->'event' AS event, hash FROM ledger.event
                           WHERE account=${c.req.param("id")} ORDER BY seq DESC LIMIT ${limit}`;
    return c.json(rows.map((r) => ({ seq: r.seq, date: r.date, kind: r.kind, hash: r.hash, text: describe(r.event as LedgerEvent) })));
  });

  app.get("/api/accounts/:id/orders", async (c) => {
    const rows = await sql`
      SELECT o.order_id, o.instrument_id, o.side, o.notional_eur::float notional, o.qty::float qty, o.order_kind,
             o.exec_date, o.status, o.fill, s.symbol, s.status AS alpaca_status, s.filled_avg_price_usd::float alpaca_price
      FROM paper.order o LEFT JOIN paper.alpaca_shadow s USING (order_id)
      WHERE o.account=${c.req.param("id")} ORDER BY o.created_at DESC LIMIT 100`;
    return c.json(rows);
  });

  // Azione: ripartenza dopo il soft stop. L'header personalizzato impedisce richieste da altri siti (CSRF):
  // un browser non può inviarlo cross-origin senza un preflight CORS, che questo server non autorizza.
  app.post("/api/accounts/:id/resume", async (c) => {
    if (c.req.header("x-money-action") !== "resume") return c.json({ ok: false, message: "richiesta non valida" }, 400);
    const id = c.req.param("id");
    const exists = await sql`SELECT 1 FROM paper.account WHERE account=${id}`;
    if (!exists.length) return c.json({ ok: false, message: "conto inesistente" }, 404);
    const r = await resume(id);
    return c.json(r, r.ok ? 200 : 409);
  });

  return app;
}
