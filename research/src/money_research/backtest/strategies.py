"""Strategie di riferimento. Le strategie vere (M4+) implementano lo stesso protocollo."""

from __future__ import annotations

from dataclasses import dataclass, field

from .simulator import Context, OrderIntent


@dataclass
class SavingsPlan:
    """Benchmark (fissato a priori): tutta la liquidità nell'ETF globale con un piano di accumulo.

    Il piano di accumulo su Trade Republic non ha commissioni: ogni versamento viene investito
    appena i guardrails lo permettono (un ordine rifiutato, ad esempio per dati vecchi il lunedì
    mattina, si riprova il giorno di borsa successivo).
    """

    instrument: str
    expected_edge_pct: float
    min_order_eur: float = 1.0
    name: str = "piano-di-accumulo"
    instruments: list[str] = field(init=False)

    def __post_init__(self) -> None:
        self.instruments = [self.instrument]

    def decide(self, ctx: Context) -> list[OrderIntent]:
        if ctx.cash_eur < self.min_order_eur:
            return []
        return [
            OrderIntent(
                instrument=self.instrument,
                side="buy",
                notional_eur=ctx.cash_eur,
                kind="savings_plan",
                expected_edge_pct=self.expected_edge_pct,
                reason="investimento della liquidità (piano di accumulo)",
            )
        ]
