"""Configurazione: variabili d'ambiente (.env) e universo degli strumenti (config/universe.toml)."""

from __future__ import annotations

import os
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[3]
UNIVERSE_PATH = REPO_ROOT / "config" / "universe.toml"

ASSET_CLASSES = {"stock_us", "etf_ucits", "etf_us", "crypto_etp", "crypto_spot"}
TAX_CATEGORIES = {"RD", "RC", "CRYPTO"}
PRICE_SOURCES = {"alpaca_stock", "alpaca_crypto"}


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Proxy:
    source: str
    symbol: str
    quote_currency: str


@dataclass(frozen=True)
class Instrument:
    id: str
    name: str
    asset_class: str
    currency: str
    tax_category: str
    sleeves: tuple[str, ...]
    proxy: Proxy
    isin: str | None = None
    notes: str | None = None


def isin_is_valid(isin: str) -> bool:
    """Verifica formato e cifra di controllo (Luhn sulle cifre ottenute da A=10..Z=35)."""
    if not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}[0-9]", isin):
        return False
    digits = "".join(str(int(c, 36)) for c in isin)
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def load_universe(path: Path = UNIVERSE_PATH) -> list[Instrument]:
    data = tomllib.loads(path.read_text())
    out: list[Instrument] = []
    seen: set[str] = set()
    errors: list[str] = []
    for raw in data.get("instrument", []):
        iid = raw.get("id", "?")
        if iid in seen:
            errors.append(f"{iid}: id duplicato")
        seen.add(iid)
        if raw.get("asset_class") not in ASSET_CLASSES:
            errors.append(f"{iid}: asset_class non valida")
        if raw.get("tax_category") not in TAX_CATEGORIES:
            errors.append(f"{iid}: tax_category non valida")
        isin = raw.get("isin") or None
        if isin and not isin_is_valid(isin):
            errors.append(f"{iid}: ISIN {isin} non valido")
        p = raw.get("proxy") or {}
        if p.get("source") not in PRICE_SOURCES or not p.get("symbol"):
            errors.append(f"{iid}: proxy mancante o fonte non supportata")
            continue
        out.append(
            Instrument(
                id=iid,
                name=raw["name"],
                asset_class=raw["asset_class"],
                currency=raw["currency"],
                tax_category=raw["tax_category"],
                sleeves=tuple(raw.get("sleeves", [])),
                proxy=Proxy(p["source"], p["symbol"], p.get("quote_currency", "USD")),
                isin=isin,
                notes=raw.get("notes"),
            )
        )
    if errors:
        raise ConfigError("universe.toml non valido: " + "; ".join(errors))
    return out


@dataclass(frozen=True)
class Settings:
    database_url: str
    alpaca_key_id: str
    alpaca_secret_key: str
    alpaca_feed: str

    @property
    def has_alpaca_keys(self) -> bool:
        return bool(self.alpaca_key_id and self.alpaca_secret_key)


def load_settings() -> Settings:
    load_dotenv(REPO_ROOT / ".env")
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        raise ConfigError("DATABASE_URL mancante: copia .env.example in .env e compilalo")
    return Settings(
        database_url=url,
        alpaca_key_id=os.environ.get("ALPACA_KEY_ID", ""),
        alpaca_secret_key=os.environ.get("ALPACA_SECRET_KEY", ""),
        alpaca_feed=os.environ.get("ALPACA_FEED", "sip") or "sip",
    )
