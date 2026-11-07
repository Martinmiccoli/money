import { describe as suite, expect, it } from "vitest";
import type { Sql } from "postgres";
import { createApp } from "../server/app";
import { describe, maxDrawdown, positionsFromFills } from "../server/format";

suite("testo degli eventi", () => {
  it("descrive fill, rifiuti e rischio in italiano", () => {
    expect(describe({ kind: "Fill", side: "buy", qty: "0.5", instrument: "all_world", price_eur: "100.05", commission_eur: "0" }))
      .toBe("Comprate 0,5 quote di all_world a 100,05 € (commissione 0,00 €)");
    expect(describe({ kind: "OrderRejected", side: "buy", instrument: "x", codes: ["G-06"] })).toBe(
      "Ordine bloccato [G-06]: compra x",
    );
    expect(describe({ kind: "RiskStateChanged", from: "Active", to: "Suspended", equity_eur: "850" })).toContain(
      "Active → Suspended",
    );
  });
});

suite("posizioni e drawdown", () => {
  it("somma acquisti e vendite e toglie le posizioni chiuse", () => {
    const p = positionsFromFills([
      { instrument: "a", side: "buy", qty: "2" },
      { instrument: "b", side: "buy", qty: "1" },
      { instrument: "b", side: "sell", qty: "1" },
      { instrument: "a", side: "sell", qty: "0.5" },
    ]);
    expect([...p]).toEqual([["a", 1.5]]);
  });
  it("calcola il massimo drawdown", () => {
    expect(maxDrawdown([100, 120, 90, 130])).toBeCloseTo(-0.25);
    expect(maxDrawdown([])).toBe(0);
  });
});

suite("azione di ripartenza", () => {
  const sql = ((..._args: unknown[]) => Promise.resolve([{ ok: 1 }])) as unknown as Sql;
  const app = createApp(sql, async (a) => ({ ok: true, message: `ripartito ${a}` }));

  it("senza l'header di sicurezza viene rifiutata (protezione CSRF)", async () => {
    const r = await app.request("/api/accounts/paper-50/resume", { method: "POST" });
    expect(r.status).toBe(400);
  });
  it("con l'header chiama il motore", async () => {
    const r = await app.request("/api/accounts/paper-50/resume", { method: "POST", headers: { "x-money-action": "resume" } });
    expect(r.status).toBe(200);
    expect(await r.json()).toEqual({ ok: true, message: "ripartito paper-50" });
  });
});
