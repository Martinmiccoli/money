"""Form 4 dalla SEC: dataset trimestrali "Insider Transactions" (Form 3/4/5 strutturati, dal 2006).

https://www.sec.gov/dera/data/form-345 — un file zip per trimestre (per data di deposito). Si tengono
solo le transazioni su azioni (tabella non-derivati) con codice **P** (acquisto sul mercato aperto) o
**S** (vendita), dai Form 4 originali (gli emendamenti 4/A si ignorano per non contare due volte).

Fair-access policy della SEC: User-Agent con nome ed email (SEC_CONTACT in .env), poche richieste.
I file scaricati restano in data/sec/ (ignorata da git) per non riscaricarli.
"""

from __future__ import annotations

import io
import logging
import os
import time
import zipfile
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import pandas as pd
import psycopg

from ..config import REPO_ROOT

log = logging.getLogger(__name__)
NY = ZoneInfo("America/New_York")
URL = "https://www.sec.gov/files/structureddata/data/insider-transactions-data-sets/{q}_form345.zip"
CACHE = REPO_ROOT / "data" / "sec"


def sec_headers() -> dict[str, str]:
    contact = os.environ.get("SEC_CONTACT", "").strip().strip('"')
    if not contact:
        raise RuntimeError("SEC_CONTACT mancante in .env: la SEC richiede nome ed email nello User-Agent")
    return {"User-Agent": contact}


def quarters(start: date, end: date) -> list[str]:
    out, y, q = [], start.year, (start.month - 1) // 3 + 1
    while (y, q) <= (end.year, (end.month - 1) // 3 + 1):
        out.append(f"{y}q{q}")
        y, q = (y + 1, 1) if q == 4 else (y, q + 1)
    return out


def download(q: str, client: httpx.Client | None = None, force: bool = False) -> Path | None:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{q}_form345.zip"
    if path.exists() and not force:
        return path
    c = client or httpx.Client(timeout=300, headers=sec_headers(), follow_redirects=True)
    r = c.get(URL.format(q=q))
    time.sleep(1.0)  # cortesia verso la SEC
    if r.status_code == 404:
        return None  # trimestre non ancora pubblicato
    r.raise_for_status()
    path.write_bytes(r.content)
    return path


def _read(z: zipfile.ZipFile, name: str, cols: list[str]) -> pd.DataFrame:
    """Legge le colonne richieste; quelle assenti nei trimestri più vecchi diventano vuote."""
    with z.open(name) as f:
        header = f.readline().decode("utf-8", errors="replace").rstrip("\r\n").split("\t")
    present = [c for c in cols if c in header]
    with z.open(name) as f:
        df = pd.read_csv(
            io.TextIOWrapper(f, encoding="utf-8", errors="replace"),
            sep="\t",
            usecols=present,
            dtype=str,
            quoting=3,
            on_bad_lines="skip",
        )
    for c in cols:
        if c not in df:
            df[c] = None
    return df


def parse(zip_bytes: bytes) -> pd.DataFrame:
    """Unisce deposito, insider e transazioni. Una riga per transazione P/S su azioni."""
    z = zipfile.ZipFile(io.BytesIO(zip_bytes))
    sub = _read(
        z,
        "SUBMISSION.tsv",
        ["ACCESSION_NUMBER", "FILING_DATE", "DOCUMENT_TYPE", "ISSUERCIK", "ISSUERTRADINGSYMBOL", "AFF10B5ONE"],
    )
    sub = sub[sub["DOCUMENT_TYPE"] == "4"]
    own = _read(
        z,
        "REPORTINGOWNER.tsv",
        ["ACCESSION_NUMBER", "RPTOWNERCIK", "RPTOWNERNAME", "RPTOWNER_RELATIONSHIP", "RPTOWNER_TITLE"],
    )
    # Depositi congiunti (es. fondo e gestore): si tiene il primo dichiarante per non contare due volte.
    own = own.drop_duplicates("ACCESSION_NUMBER", keep="first")
    tr = _read(
        z,
        "NONDERIV_TRANS.tsv",
        [
            "ACCESSION_NUMBER",
            "NONDERIV_TRANS_SK",
            "TRANS_DATE",
            "TRANS_CODE",
            "TRANS_SHARES",
            "TRANS_PRICEPERSHARE",
            "SHRS_OWND_FOLWNG_TRANS",
        ],
    )
    tr = tr[tr["TRANS_CODE"].isin(["P", "S"])]
    df = tr.merge(sub, on="ACCESSION_NUMBER").merge(own, on="ACCESSION_NUMBER", how="left")
    # Piani 10b5-1: flag ufficiale solo dal 2023 (AFF10B5ONE). Prima si cerca "10b5-1" nelle note del
    # filing (approssimazione: vale per tutte le transazioni di quel filing).
    fn = _read(z, "FOOTNOTES.tsv", ["ACCESSION_NUMBER", "FOOTNOTE_TXT"])
    planned = set(fn.loc[fn["FOOTNOTE_TXT"].fillna("").str.contains(r"10b5-?1", case=False), "ACCESSION_NUMBER"])
    df["PLAN_FN"] = df["ACCESSION_NUMBER"].isin(planned)

    def d(s: pd.Series) -> pd.Series:
        return pd.to_datetime(s, format="%d-%b-%Y", errors="coerce").dt.date

    out = pd.DataFrame(
        {
            "accession_no": df["ACCESSION_NUMBER"],
            "trans_sk": pd.to_numeric(df["NONDERIV_TRANS_SK"], errors="coerce"),
            "issuer_cik": df["ISSUERCIK"].str.lstrip("0"),
            "symbol": df["ISSUERTRADINGSYMBOL"].str.strip().str.upper(),
            "owner_cik": df["RPTOWNERCIK"].fillna("").str.lstrip("0"),
            "owner_name": df["RPTOWNERNAME"],
            "relationship": df["RPTOWNER_RELATIONSHIP"],
            "officer_title": df["RPTOWNER_TITLE"],
            "trans_code": df["TRANS_CODE"],
            "trans_date": d(df["TRANS_DATE"]),
            "shares": pd.to_numeric(df["TRANS_SHARES"], errors="coerce"),
            "price": pd.to_numeric(df["TRANS_PRICEPERSHARE"], errors="coerce"),
            "shares_after": pd.to_numeric(df["SHRS_OWND_FOLWNG_TRANS"], errors="coerce"),
            "is_10b5_1": df["AFF10B5ONE"].fillna("0").isin(["1", "true", "TRUE"]) | df["PLAN_FN"],
            "filing_date": d(df["FILING_DATE"]),
        }
    )
    out = out.dropna(subset=["trans_sk", "filing_date"])
    out = out[out["owner_cik"] != ""]
    # G-11: il dataset ha solo la data di deposito; la SEC accetta filing fino alle 22:00 di New York.
    out["available_at"] = [
        datetime.combine(x, datetime.min.time().replace(hour=22), tzinfo=NY) for x in out["filing_date"]
    ]
    return out


def store(conn: psycopg.Connection, df: pd.DataFrame) -> int:
    cols = [
        "accession_no", "trans_sk", "issuer_cik", "symbol", "owner_cik", "owner_name", "relationship",
        "officer_title", "trans_code", "trans_date", "shares", "price", "shares_after", "is_10b5_1",
        "filing_date", "available_at",
    ]  # fmt: skip
    rows = [
        tuple(None if (isinstance(v, float) and v != v) else v for v in r) for r in df[cols].itertuples(index=False)
    ]
    with conn.transaction(), conn.cursor() as cur:
        cur.executemany(
            f"INSERT INTO raw.form4 ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))}) "
            "ON CONFLICT (accession_no, trans_sk) DO NOTHING",
            rows,
        )
    return len(rows)


def ingest(conn: psycopg.Connection, start: date, end: date, force_last: bool = True) -> dict[str, int]:
    """Scarica e carica i trimestri. L'ultimo trimestre si riscarica sempre (è ancora in corso)."""
    out = {}
    qs = quarters(start, end)
    for i, q in enumerate(qs):
        path = download(q, force=force_last and i == len(qs) - 1)
        if path is None:
            out[q] = 0
            continue
        out[q] = store(conn, parse(path.read_bytes()))
        log.info("Form 4 %s: %d transazioni", q, out[q])
    return out
