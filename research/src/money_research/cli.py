"""CLI `money`: uv run money <comando>.

money db migrate               applica le migrazioni SQL
money universe sync            carica config/universe.toml nel DB
money ingest fx                cambi BCE (nessuna chiave)
money ingest rates             tassi €STR ed EONIA (privo di rischio per lo Sharpe)
money ingest prices            prezzi giornalieri dei proxy (Alpaca; crypto anche senza chiavi)
money ingest all               tutto quanto sopra (incluse migrazioni e universo)
money status                   copertura dei dati e ultime esecuzioni
money chart [id ...]           grafico dei prezzi in EUR (base 100) in reports/charts/
money backtest benchmark       report del benchmark (piano di accumulo) in reports/validation/
money backtest m4              strategie ETF S3/S4/S8: griglia a priori, registro G-12, report
money paper run-day            giornata di paper trading: ingest → feed → settle → decide → execute
money paper status             riepilogo dei conti paper (Gate 1)
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, timedelta

from . import db
from .config import REPO_ROOT, ConfigError, load_settings, load_universe
from .ingest import ecb, prices
from .ingest.alpaca import AlpacaData, AlpacaError

log = logging.getLogger("money")


def _conn():
    return db.connect(load_settings().database_url)


def cmd_migrate(_args) -> None:
    with _conn() as c:
        done = db.migrate(c)
    print("migrazioni applicate:", ", ".join(done) if done else "nessuna (DB già aggiornato)")


def cmd_universe(_args) -> None:
    inst = load_universe()
    with _conn() as c:
        n = db.sync_universe(c, inst)
    print(f"universo sincronizzato: {n} strumenti")


def cmd_fx(args) -> None:
    with _conn() as c, db.ingest_run(c, "fx_ecb") as run:
        last = c.execute("SELECT max(date) FROM market.fx_1d WHERE pair='EURUSD'").fetchone()[0]
        start = args.start or (last - timedelta(days=7) if last else prices.DEFAULT_START)
        rates = ecb.fetch_eur_rates("USD", start)
        run["rows"] = ecb.store(c, rates)
    print(f"cambi BCE EURUSD: {len(rates)} righe da {start}")


def cmd_rates(args) -> None:
    with _conn() as c, db.ingest_run(c, "rates_ecb") as run:
        total = 0
        for series in ecb.RATE_SERIES:
            last = c.execute("SELECT max(date) FROM market.rate_1d WHERE series=%s", (series,)).fetchone()[0]
            if series == "EONIA" and last and last >= ecb.ESTR_START:
                continue  # serie chiusa: basta lo storico fino all'avvio dell'€STR
            start = args.start or (last - timedelta(days=7) if last else prices.DEFAULT_START)
            total += ecb.store_rates(c, ecb.fetch_rates(series, start))
        run["rows"] = total
    print(f"tassi BCE (€STR, EONIA): {total} righe")


def cmd_prices(args) -> None:
    s = load_settings()
    inst = load_universe()
    if not s.has_alpaca_keys:
        print("⚠️  chiavi Alpaca assenti: scarico solo le crypto (le azioni/ETF richiedono le chiavi)")
        inst = [i for i in inst if i.proxy.source == "alpaca_crypto"]
    client = AlpacaData(s.alpaca_key_id, s.alpaca_secret_key, s.alpaca_feed)
    with db.connect(s.database_url) as c, db.ingest_run(c, "prices_alpaca") as run:
        start = args.start or prices.incremental_start(inst, prices.last_dates(c))
        rows = prices.fetch(client, inst, start, args.end)
        run["rows"] = prices.store(c, rows)
        missing = sorted({i.id for i in inst} - {r.instrument_id for r in rows})
        if missing:
            run["status"], run["detail"] = "partial", "nessun dato per: " + ", ".join(missing)
    print(f"prezzi: {len(rows)} barre da {start} (feed {client.feed})")
    if missing:
        print("⚠️  nessun dato per:", ", ".join(missing))


def cmd_all(args) -> None:
    cmd_migrate(args)
    cmd_universe(args)
    cmd_fx(args)
    cmd_rates(args)
    cmd_prices(args)


def cmd_status(_args) -> None:
    with _conn() as c:
        rows = c.execute(
            """SELECT i.instrument_id, m.source_symbol, count(b.date), min(b.date), max(b.date)
               FROM ref.instrument i
               LEFT JOIN ref.instrument_map m USING (instrument_id)
               LEFT JOIN market.bar_1d b USING (instrument_id)
               GROUP BY 1, 2 ORDER BY 1"""
        ).fetchall()
        fx = c.execute("SELECT count(*), min(date), max(date) FROM market.fx_1d WHERE pair='EURUSD'").fetchone()
        runs = c.execute(
            "SELECT job, status, finished_at, rows_written, coalesce(detail,'') FROM ops.ingest_run "
            "ORDER BY run_id DESC LIMIT 6"
        ).fetchall()
    print(f"{'strumento':24} {'proxy':9} {'barre':>6}  {'dal':10}  {'al':10}")
    for iid, sym, n, lo, hi in rows:
        print(f"{iid:24} {sym or '-':9} {n:>6}  {str(lo or '-'):10}  {str(hi or '-'):10}")
    print(f"\ncambi EURUSD: {fx[0]} giorni, {fx[1]} → {fx[2]}")
    print("\nultime esecuzioni:")
    for job, st, fin, n, det in runs:
        print(f"  {fin:%Y-%m-%d %H:%M}  {job:14} {st:8} {n:>6} righe  {det[:80]}" if fin else f"  {job} {st}")


def cmd_chart(args) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pandas as pd

    with _conn() as c:
        ids = args.ids or ["all_world", "us_equity", "gold", "bitcoin_etp"]
        bars = pd.DataFrame(
            c.execute(
                "SELECT instrument_id, date, coalesce(adj_close, close), currency FROM market.bar_1d "
                "WHERE instrument_id = ANY(%s) ORDER BY date",
                (ids,),
            ).fetchall(),
            columns=["id", "date", "px", "ccy"],
        )
        fx = pd.DataFrame(
            c.execute("SELECT date, rate FROM market.fx_1d WHERE pair='EURUSD' ORDER BY date").fetchall(),
            columns=["date", "eurusd"],
        )
    if bars.empty:
        sys.exit("nessun dato: esegui prima `money ingest all`")
    bars["date"] = pd.to_datetime(bars["date"])
    fx["date"] = pd.to_datetime(fx["date"])
    # Conversione in EUR con l'ultimo cambio BCE disponibile (as-of, nessun dato futuro).
    bars = pd.merge_asof(bars.sort_values("date"), fx.sort_values("date"), on="date")
    bars["px_eur"] = bars["px"].where(bars["ccy"] == "EUR", bars["px"] / bars["eurusd"])
    wide = bars.pivot_table(index="date", columns="id", values="px_eur").dropna(how="all")
    wide = wide.loc[wide.dropna().index.min() :] if not wide.dropna().empty else wide
    # Le crypto quotano anche nel weekend: per gli ETF si tiene l'ultimo prezzo noto (solo passato).
    wide = wide.ffill()
    norm = wide / wide.iloc[0] * 100
    out_dir = REPO_ROOT / "reports" / "charts"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"prezzi-eur-{date.today():%Y%m%d}.png"
    ax = norm.plot(figsize=(11, 6), logy=True, title="Prezzi in EUR (base 100, scala log) — proxy rettificati")
    ax.set_xlabel("")
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(out, dpi=120)
    print(f"grafico salvato in {out}")


def cmd_backtest_benchmark(args) -> None:
    from .backtest.run import benchmark_report

    with _conn() as c:
        path, sha = benchmark_report(c)
    print(f"report: {path}")
    print(f"sha256: {sha}")


def cmd_backtest_m4(args) -> None:
    from .backtest.run import m4_report

    with _conn() as c:
        path, sha = m4_report(c)
    print(f"report: {path}")
    print(f"sha256: {sha}")


def cmd_paper_run_day(args) -> None:
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from .backtest.run import load_validation
    from .paper import feed as pfeed
    from .paper import runner

    now = datetime.fromisoformat(args.now) if args.now else datetime.now(ZoneInfo("Europe/Rome"))
    if now.tzinfo is None:
        sys.exit("--now deve includere il fuso orario, es. 2026-11-09T09:00:00+01:00")
    if not args.skip_ingest:
        cmd_all(args)
    accounts = runner.load_accounts()
    val = load_validation()
    with _conn() as c, db.ingest_run(c, "paper_day") as run:
        db.migrate(c)
        new = runner.sync_accounts(c, accounts, now.astimezone(runner.ROME).date())
        if new:
            print(f"conti paper creati: {new}")
        first = c.execute("SELECT min(started_on) FROM paper.account").fetchone()[0]
        added = pfeed.update_feed(
            c,
            runner.all_instruments(accounts),
            pfeed.default_anchor(first),
            val["proxy_drag_bps_per_year"],
            set(val["fx_hedged"]),
        )
        print(f"feed prezzi EUR: {added} righe nuove")
        print(runner.engine("settle", now))
        for acct, msg in runner.decide(c, accounts, now).items():
            print(f"decisione {acct}: {msg}")
        print(runner.engine("execute", now))
        run["rows"] = added


def cmd_paper_status(args) -> None:
    from .paper import runner

    with _conn() as c:
        rows = runner.status_rows(c)
    if not rows:
        print("nessun conto paper: esegui `money paper run-day`")
        return
    for r in rows:
        val = f"{r['valore']:.2f} €" if r["valore"] is not None else "—"
        ret = f"{r['rendimento'] * 100:+.2f}%" if r["rendimento"] is not None else "—"
        print(
            f"{r['conto']:<12} {r['strategia']:<18} dal {r['dal']}  giorni {r['giorni']:>3}  valore {val:>12}  "
            f"rendimento {ret:>8}  max DD {r['max_dd'] * 100:6.2f}%  eseguiti {r['eseguiti']:>3}  "
            f"rischio {r['rischio']}  rifiuti: {r['rifiutati']}"
        )


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    p = argparse.ArgumentParser(prog="money", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("db").add_subparsers(dest="sub", required=True).add_parser("migrate").set_defaults(fn=cmd_migrate)
    sub.add_parser("universe").add_subparsers(dest="sub", required=True).add_parser("sync").set_defaults(
        fn=cmd_universe
    )
    ing = sub.add_parser("ingest").add_subparsers(dest="sub", required=True)
    for name, fn in [("fx", cmd_fx), ("rates", cmd_rates), ("prices", cmd_prices), ("all", cmd_all)]:
        sp = ing.add_parser(name)
        sp.add_argument("--start", type=date.fromisoformat, help="AAAA-MM-GG (default: incrementale)")
        sp.add_argument("--end", type=date.fromisoformat)
        sp.set_defaults(fn=fn)
    sub.add_parser("status").set_defaults(fn=cmd_status)
    ch = sub.add_parser("chart")
    ch.add_argument("ids", nargs="*")
    ch.set_defaults(fn=cmd_chart)
    bt = sub.add_parser("backtest").add_subparsers(dest="sub", required=True)
    bt.add_parser("benchmark").set_defaults(fn=cmd_backtest_benchmark)
    bt.add_parser("m4").set_defaults(fn=cmd_backtest_m4)
    pp = sub.add_parser("paper").add_subparsers(dest="sub", required=True)
    rd = pp.add_parser("run-day")
    rd.add_argument("--now", help="istante della decisione (ISO con fuso), per recuperi e test")
    rd.add_argument("--skip-ingest", action="store_true", help="non riscaricare i dati")
    rd.set_defaults(fn=cmd_paper_run_day, start=None, end=None)
    pp.add_parser("status").set_defaults(fn=cmd_paper_status)

    args = p.parse_args(argv)
    try:
        args.fn(args)
    except (ConfigError, AlpacaError) as e:
        sys.exit(f"errore: {e}")


if __name__ == "__main__":
    main()
